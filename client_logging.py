# client_logging.py
import os
import zipfile
import time
import csv
import requests
import subprocess
import psutil
import socket

from carbon_api import get_zone_carbon_g_per_kwh
from train_decision import train_and_save

# -----------------------------
# CONFIG
# -----------------------------
CLOUD_URL = "http://65.2.138.36:8000/run-task"  # e.g. Stockholm or Mumbai
CSV_PATH = "telemetry_labeled.csv"

# Zones
LOCAL_ZONE = "IN-WE"
CLOUD_ZONE = "SE-SE4"  # or "IN-WE" if logging Mumbai

# Estimated local + cloud power draw (demo values — adjust later)
LOCAL_POWER_WATTS = 45      # typical laptop load
CLOUD_POWER_WATTS = 35      # more efficient server for demo

# -----------------------------
# ZIP TASK
# -----------------------------
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

# -----------------------------
# RUN LOCAL VERSION
# -----------------------------
def measure_local_run(command=["python3", "train.py"], cwd="task"):
    start = time.time()
    proc = subprocess.run(command, cwd=cwd)
    end = time.time()
    return end - start, proc.returncode == 0

# -----------------------------
# RUN CLOUD VERSION
# -----------------------------
def upload_and_time(zip_path, url=CLOUD_URL, timeout=300):
    with open(zip_path, "rb") as f:
        start = time.time()
        r = requests.post(url, files={"file": f}, timeout=timeout)
        end = time.time()
    if r.status_code == 200:
        with open("output_logged.zip", "wb") as out:
            out.write(r.content)
    return end - start, r.status_code == 200, r.status_code

# -----------------------------
# BASIC NETWORK PING
# -----------------------------
def get_basic_network_latency():
    try:
        s = socket.socket()
        s.settimeout(1)
        t0 = time.time()
        s.connect(("8.8.8.8", 53))
        t1 = time.time()
        s.close()
        return (t1 - t0) * 1000
    except Exception:
        return 9999.0

# -----------------------------
# DEVICE STATE (CPU/BATTERY)
# -----------------------------
def get_device_state():
    cpu = psutil.cpu_percent(interval=0.3)
    batt = psutil.sensors_battery()
    battery_percent = batt.percent if batt else -1
    is_charging = int(batt.power_plugged) if batt else -1
    gpu_available = 0  # could be extended later
    return {
        "cpu_percent": cpu,
        "battery_percent": battery_percent,
        "is_charging": is_charging,
        "gpu_available": gpu_available
    }

# -----------------------------
# CSV APPEND
# -----------------------------
def append_csv_row(row):
    write_header = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(row)
    try:
        train_and_save(quiet=True)
    except Exception as exc:
        print(f"[logger] Warning: model retrain skipped ({exc})")

# -----------------------------
# RUN ONE TASK + LOG ROW
# -----------------------------
def run_and_log():
    zip_path = make_zip("task")

    # network + system state before running
    rtt_ms = get_basic_network_latency()
    dev = get_device_state()
    input_size = os.path.getsize(zip_path)

    # 1) LOCAL RUN
    local_time_s, local_ok = measure_local_run()

    # 2) CLOUD RUN
    cloud_time_s, cloud_ok, cloud_status = upload_and_time(zip_path)

    # 3) CARBON / ENERGY calculations (using real carbon_api)
    local_ci = get_zone_carbon_g_per_kwh(LOCAL_ZONE)
    cloud_ci = get_zone_carbon_g_per_kwh(CLOUD_ZONE)

    local_energy_kwh = (LOCAL_POWER_WATTS * local_time_s) / (3600.0 * 1000)
    cloud_energy_kwh = (CLOUD_POWER_WATTS * cloud_time_s) / (3600.0 * 1000)

    local_co2_g = local_energy_kwh * local_ci
    cloud_co2_g = cloud_energy_kwh * cloud_ci

    # Simple rule label: is offloading better than local?
    carbon_margin = 0.85   # require cloud to be at least 15% cleaner
    time_margin = 1.2      # cloud must be < 20% slower

    offload_better = int(
        (cloud_co2_g < local_co2_g * carbon_margin) and
        (cloud_time_s < local_time_s * time_margin)
    )

    co2_saved = local_co2_g - cloud_co2_g
    co2_saved_pct = (co2_saved / local_co2_g * 100.0) if local_co2_g > 0 else 0.0

    row = {
        "timestamp": time.time(),
        "input_size_bytes": input_size,
        "local_time_s": local_time_s,
        "cloud_time_s": cloud_time_s,
        "local_ok": local_ok,
        "cloud_ok": cloud_ok,
        "cloud_http_status": cloud_status,
        "rtt_ms": rtt_ms,
        "cpu_percent": dev["cpu_percent"],
        "battery_percent": dev["battery_percent"],
        "is_charging": dev["is_charging"],
        "gpu_available": dev["gpu_available"],
        "local_ci_g_per_kwh": local_ci,
        "cloud_ci_g_per_kwh": cloud_ci,
        "local_co2_g": local_co2_g,
        "cloud_co2_g": cloud_co2_g,
        "co2_saved_g": co2_saved,
        "co2_saved_pct": co2_saved_pct,
        "offload_better": offload_better,
    }

    append_csv_row(row)
    print("\nLogged:", row, "\n")


if __name__ == "__main__":
    for i in range(5):     # run 5 samples for demo
        print(f"=== Log Run {i+1} ===")
        run_and_log()
        time.sleep(1)
