# decide_and_run.py
import os
import time
import zipfile
import subprocess
import requests
import psutil
import socket
import joblib

CLOUD_URL = "https://offload-demo.onrender.com/run-task"  # same as before
MODEL_PATH = "decision_model_lgb.joblib"

# ---------- helpers (same style as before) ----------

def get_basic_network_latency():
    try:
        s = socket.socket()
        s.settimeout(1)
        t0 = time.time()
        s.connect(("8.8.8.8", 53))
        t1 = time.time()
        s.close()
        return (t1 - t0) * 1000
    except:
        return 9999.0

def get_device_state():
    cpu = psutil.cpu_percent(interval=0.3)
    batt = psutil.sensors_battery()
    battery_percent = batt.percent if batt else -1
    is_charging = int(batt.power_plugged) if batt else -1
    gpu_available = 0  # placeholder
    return cpu, battery_percent, is_charging, gpu_available

def make_zip(src_folder="task", zip_name="task.zip"):
    if os.path.exists(zip_name):
        os.remove(zip_name)
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_folder):
            for file in files:
                full = os.path.join(root, file)
                arc = os.path.relpath(full, start=src_folder)
                zf.write(full, os.path.join("task", arc))
    return zip_name

def run_local():
    print("➡ Running locally...")
    start = time.time()
    proc = subprocess.run(["python3", "train.py"], cwd="task")
    end = time.time()
    print(f"Local finished in {end - start:.2f}s (returncode={proc.returncode})")

def run_cloud():
    print("➡ Offloading to cloud...")
    zip_path = make_zip("task")
    with open(zip_path, "rb") as f:
        start = time.time()
        r = requests.post(CLOUD_URL, files={"file": f}, timeout=300)
        end = time.time()
    if r.status_code == 200:
        with open("output.zip", "wb") as out:
            out.write(r.content)
        print(f"Cloud finished in {end - start:.2f}s, output.zip saved.")
    else:
        print("Cloud error:", r.status_code, r.text[:200])

# ---------- main decision logic ----------

def main():
    # Load rule bundle
    bundle = joblib.load(MODEL_PATH)
    rules = bundle["rules"]
    feature_cols = bundle["feature_cols"]

    # Collect features
    zip_path = make_zip("task")
    input_size_bytes = os.path.getsize(zip_path)
    rtt_ms = get_basic_network_latency()
    cpu_percent, battery_percent, is_charging, gpu_available = get_device_state()

    # Safety guard: if battery super low, prefer cloud (or your policy)
    if battery_percent != -1 and battery_percent < 5 and not is_charging:
        print("Battery very low, but as a simple policy we still try cloud.")
        # you can flip this to run_local() if you prefer
        run_cloud()
        return

    # Build feature vector in the same order as training
    feat_dict = {
        "input_size_bytes": input_size_bytes,
        "rtt_ms": rtt_ms,
        "cpu_percent": cpu_percent,
        "battery_percent": battery_percent,
        "is_charging": is_charging,
        "gpu_available": gpu_available,
    }
    # Evaluate rule set
    def apply_rules(ruleset, features):
        for rule in ruleset:
            match = True
            for cond in rule["conditions"]:
                value = features[cond["feature"]]
                threshold = cond["threshold"]
                if cond["op"] == "<=":
                    if not value <= threshold:
                        match = False
                        break
                else:  # operator ">"
                    if not value > threshold:
                        match = False
                        break
            if match:
                return rule
        return None

    matched_rule = apply_rules(rules, feat_dict)

    if matched_rule is None:
        print("No matching rule found; defaulting to cloud execution.")
        run_cloud()
        return

    decision = matched_rule["decision"]
    probability = matched_rule["probability"]
    cond_text = " AND ".join(
        f"{c['feature']} {c['op']} {c['threshold']:.4f}" for c in matched_rule["conditions"]
    ) or "<any>"
    print(
        f"Matched rule -> {decision} (p={probability:.2f})\n  Conditions: {cond_text}"
    )

    if decision == "cloud":
        run_cloud()
    else:
        run_local()

if __name__ == "__main__":
    main()
