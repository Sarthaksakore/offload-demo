# client.py
import requests
import sys

BASE_URL = "http://13.127.171.164:8000"  # your Render URL

def run_task(zip_path: str):
    url = f"{BASE_URL}/run-task"   # 👈 IMPORTANT: /run-task
    files = {"file": open(zip_path, "rb")}

    print(f"Uploading {zip_path} to cloud...")
    resp = requests.post(url, files=files)

    if resp.status_code == 200:
        with open("output.zip", "wb") as f:
            f.write(resp.content)
        print("Got output.zip from cloud!")
    else:
        print(f"Cloud error: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    zip_path = "task.zip" if len(sys.argv) < 2 else sys.argv[1]
    run_task(zip_path)
