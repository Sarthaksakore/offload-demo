# main.py

import os
import zipfile
import shutil
import uuid
import subprocess

import requests
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ---------- ENV SETUP ----------

load_dotenv()

ELECTRICITY_MAPS_API_KEY = os.getenv("ELECTRICITY_MAPS_API_KEY")
DEFAULT_REGION = os.getenv("DEFAULT_REGION", "IN-MH")

# ---------- FASTAPI APP ----------

app = FastAPI()
# Allow requests from your HTML file / any frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # you can restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- GREEN AI REQUEST MODEL ----------

class GreenAIRequest(BaseModel):
    question: str

# ---------- CARBON INTENSITY HELPER ----------

def fetch_carbon_intensity(region: str = None):
    """
    Fetch latest carbon intensity for the given region from ElectricityMaps API.
    Returns a dict with: region, carbon_intensity, unit
    """
    if region is None:
        region = DEFAULT_REGION

    if not ELECTRICITY_MAPS_API_KEY:
        # If API key is missing, return a placeholder
        return {
            "region": region,
            "carbon_intensity": None,
            "unit": "gCO2eq/kWh",
            "error": "Missing ELECTRICITY_MAPS_API_KEY",
        }

    url = f"https://api.electricitymap.org/v3/carbon-intensity/latest?zone={region}"
    headers = {"auth-token": ELECTRICITY_MAPS_API_KEY}

    try:
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        return {
            "region": region,
            "carbon_intensity": data.get("carbonIntensity"),
            "unit": data.get("carbonIntensityUnits", "gCO2eq/kWh"),
        }
    except Exception as e:
        print("Error fetching carbon intensity:", e)
        return {
            "region": region,
            "carbon_intensity": None,
            "unit": "gCO2eq/kWh",
            "error": str(e),
        }

# ---------- PUBLIC CARBON INTENSITY ENDPOINT ----------

@app.get("/carbon-intensity")
def get_carbon_intensity(region: str = DEFAULT_REGION):
    """
    HTTP endpoint to expose current carbon intensity.
    """
    return fetch_carbon_intensity(region)

# ---------- GREEN AI (OLLAMA) ENDPOINT ----------

OLLAMA_URL = "http://localhost:11434/api/chat"
GREEN_MODEL_NAME = "greenai"  # your custom Ollama model name

@app.post("/greenai")
def ask_green_ai(req: GreenAIRequest):
    """
    1) Fetch current carbon intensity.
    2) Send user's question to local Ollama (greenai model).
    3) Prepend carbon info to the AI's answer.
    """
    # 1) Get carbon info
    carbon = fetch_carbon_intensity()
    ci = carbon.get("carbon_intensity")
    unit = carbon.get("unit", "gCO2eq/kWh")
    region = carbon.get("region")

    if ci is not None:
        carbon_line = f"Current carbon intensity in region {region}: {ci} {unit}.\n\n"
    else:
        carbon_line = "Current carbon intensity is unavailable (API error or missing key).\n\n"

    # 2) Call Ollama local API
    payload = {
        "model": GREEN_MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": req.question,
            }
        ],
        "stream": False,
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        ai_answer = data.get("message", {}).get("content", "")
    except Exception as e:
        print("Error calling Ollama:", e)
        return {"error": "Failed to contact local GreenAI / Ollama", "details": str(e)}

    # 3) Combine carbon info + AI answer
    full_answer = carbon_line + ai_answer

    return {"answer": full_answer, "carbon": carbon}

# ---------- EXISTING /run-task ENDPOINT (YOUR CODE) ----------

WORK_BASE = "/tmp/cloud_tasks"  # Render / Linux containers have /tmp
os.makedirs(WORK_BASE, exist_ok=True)

@app.post("/run-task")
async def run_task(file: UploadFile = File(...)):
    task_id = str(uuid.uuid4())
    work_dir = os.path.join(WORK_BASE, task_id)
    os.makedirs(work_dir, exist_ok=True)

    upload_path = os.path.join(work_dir, "task.zip")
    with open(upload_path, "wb") as f:
        f.write(await file.read())

    # unzip
    try:
        with zipfile.ZipFile(upload_path, "r") as zip_ref:
            zip_ref.extractall(work_dir)
    except Exception as e:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Invalid zip: {e}")

    # run the task: expect a script at task/train.py (relative to zip root)
    task_script = os.path.join(work_dir, "task", "train.py")
    if not os.path.exists(task_script):
        # try fallback: train.py at root
        task_script = os.path.join(work_dir, "train.py")
    if not os.path.exists(task_script):
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(
            status_code=400,
            detail="No train.py found in uploaded zip (expected task/train.py or train.py)",
        )

    # run the script (synchronously). capture return code
    try:
        proc = subprocess.run(
            ["python3", task_script],
            cwd=os.path.dirname(task_script),
            timeout=60,  # safety: limit to 60s for demo. Increase if necessary.
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail="Task timed out")

    # prepare output zip
    output_dir = os.path.join(os.path.dirname(task_script), "output")
    if not os.path.exists(output_dir):
        # if no output folder produced, create one and save a default file
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "no_output.txt"), "w") as f:
            f.write("Task finished but no output folder found.")

    out_zip = os.path.join(work_dir, "output.zip")
    shutil.make_archive(out_zip.replace(".zip", ""), "zip", output_dir)

    # return file
    return FileResponse(out_zip, filename="output.zip", media_type="application/zip")
