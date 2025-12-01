# main.py
import os
import zipfile
import shutil
import uuid
import subprocess
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

WORK_BASE = "/tmp/cloud_tasks"  # Render / Linux containers have /tmp

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
        raise HTTPException(status_code=400, detail="No train.py found in uploaded zip (expected task/train.py or train.py)")

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
