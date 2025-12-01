# client.py
import requests
import zipfile
import os
import sys

CLOUD_URL = "https://<YOUR_RENDER_URL>/run-task"  # replace after deploy

def make_zip(src_folder="task", zip_name="task.zip"):
    if os.path.exists(zip_name):
        os.remove(zip_name)
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_folder):
            for file in files:
                full = os.path.join(root, file)
                arcname = os.path.relpath(full, start=src_folder)
                zf.write(full, arcname=os.path.join("task", arcname))
    return zip_name

def offload_and_get_output(url):
    zfile = make_zip()
    with open(zfile, "rb") as f:
        print("Uploading task.zip to cloud...")
        r = requests.post(url, files={"file": f}, timeout=120)
    if r.status_code == 200:
        with open("output.zip", "wb") as out:
            out.write(r.content)
        print("Received output.zip — saved locally.")
    else:
        print("Cloud error:", r.status_code, r.text)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = CLOUD_URL
    offload_and_get_output(url)
