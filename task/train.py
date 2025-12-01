# task/train.py
import time
import json
import os

# Simulate training / heavy work
time.sleep(3)

# Read optional config if present
cfg = {}
cfg_path = "config.json"
if os.path.exists(cfg_path):
    with open(cfg_path, "r") as f:
        try:
            cfg = json.load(f)
        except:
            cfg = {}

result = {
    "status": "done",
    "message": "Training simulated",
    "config_received": cfg
}

os.makedirs("output", exist_ok=True)
with open("output/result.txt", "w") as f:
    f.write("Training finished successfully.\n")
    f.write("Result JSON:\\n")
    f.write(json.dumps(result, indent=2))
