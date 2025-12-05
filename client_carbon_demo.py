# client_carbon_demo.py
import os
import zipfile
import time
import subprocess
import requests
import csv

from carbon_api import get_zone_carbon_g_per_kwh

# ----------------- CONFIG -----------------

# Two cloud instances (fill with your current IPs)
CLOUD_CONFIGS = [
    {
        "name": "mumbai",
        "url": "http://13.127.171.164:8000/run-task",   # ap-south-1
        "zone": "IN-WE",                                # Western India (live via EM API)
        "power_watts": 35,                              # assume efficient server
    },
    {
        "name": "stockholm",
        "url": "http://65.2.138.36:8000/run-task",      # eu-north-1
        "zone": "SE-SE4",                               # Stockholm region (fixed low carbon)
        "power_watts": 15,                              # even more efficient for demo
    },
]

# Local device assumptions
LOCAL_ZONE = "IN-WE"         # your local grid zone (Western India)
LOCAL_POWER_WATTS = 65       # laptop under load

# Decision margins (rule-based engine)
CARBON_MARGIN = 1.2          # cloud can emit up to 20% more CO2 vs local and still be "ok"
TIME_MARGIN = 2.0            # cloud can be up to 2x slower and still be "ok"

# Logging
DECISION_LOG_CSV = "decision_log.csv"

# ------------------------------------------


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
    print("▶ Running task locally...")
    start = time.time()
    proc = subprocess.run(["python3", "train.py"], cwd="task")
    end = time.time()
    if proc.returncode != 0:
        print("Local run failed with code", proc.returncode)
    local_time = end - start
    print(f"Local runtime: {local_time:.3f} s")
    return local_time


def run_cloud(cloud):
    """
    cloud: dict from CLOUD_CONFIGS
    Returns (time_s, ok)
    """
    url = cloud["url"]
    print(f"☁ Offloading task to cloud [{cloud['name']}] at {url} ...")
    zip_path = make_zip("task")
    try:
        with open(zip_path, "rb") as f:
            start = time.time()
            r = requests.post(url, files={"file": f}, timeout=600)
            end = time.time()
    except requests.exceptions.RequestException as e:
        print(f"Cloud [{cloud['name']}] request failed:", e)
        return None, False

    cloud_time = end - start
    if r.status_code == 200:
        with open(f"output_{cloud['name']}.zip", "wb") as out:
            out.write(r.content)
        print(f"Cloud [{cloud['name']}] returned output in {cloud_time:.3f} s")
        ok = True
    else:
        print(f"Cloud [{cloud['name']}] error:", r.status_code, r.text[:200])
        ok = False

    return cloud_time, ok


def compute_co2(time_s, power_watts, zone):
    """
    time_s: runtime in seconds
    power_watts: assumed device/server power
    zone: ElectricityMaps zone code (or handled by carbon_api)
    """
    carbon_intensity = get_zone_carbon_g_per_kwh(zone)  # gCO2/kWh
    energy_kwh = (power_watts * time_s) / (3600.0 * 1000.0)
    co2_g = energy_kwh * carbon_intensity
    return co2_g, carbon_intensity, energy_kwh


def append_decision_log(row, filename=DECISION_LOG_CSV):
    write_header = not os.path.exists(filename)
    with open(filename, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def main():
    # 1) Run locally once
    local_time = run_local()
    print()

    # 2) Run on each cloud once
    cloud_results = []
    for cloud in CLOUD_CONFIGS:
        cloud_time, cloud_ok = run_cloud(cloud)
        print()
        cloud_results.append({
            "cloud": cloud,
            "time_s": cloud_time,
            "ok": cloud_ok,
        })

    # 3) Compute CO2 for local
    local_co2, local_ci, local_energy = compute_co2(
        local_time, LOCAL_POWER_WATTS, LOCAL_ZONE
    )

    print("=== Carbon details ===")
    print(f"Local grid {LOCAL_ZONE}: {local_ci:.1f} gCO2/kWh")
    print(f"Local: {local_time:.3f}s, {local_co2:.4f} gCO2")
    print()

    # 4) Compute CO2 for each successful cloud run
    evaluated = []
    for res in cloud_results:
        cloud = res["cloud"]
        name = cloud["name"]
        if not res["ok"] or res["time_s"] is None:
            print(f"[{name}] skipped in decision (request failed).")
            continue

        time_s = res["time_s"]
        power = cloud["power_watts"]
        zone = cloud["zone"]

        co2_g, ci, energy_kwh = compute_co2(time_s, power, zone)
        print(f"Cloud [{name}] grid {zone}: {ci:.1f} gCO2/kWh")
        print(f"Cloud [{name}]: {time_s:.3f}s, {co2_g:.4f} gCO2")
        print()

        # Check if this cloud is "acceptable" compared to local (rule-based)
        cloud_ok = (co2_g <= local_co2 * CARBON_MARGIN) and \
                   (time_s <= local_time * TIME_MARGIN)

        evaluated.append({
            "name": name,
            "time_s": time_s,
            "co2_g": co2_g,
            "grid_ci": ci,
            "energy_kwh": energy_kwh,
            "acceptable": cloud_ok,
        })

    # 5) Decide best option among local + clouds
    # Start assuming local is default best
    best_where = "local"
    best_time = local_time
    best_co2 = local_co2

    # Prefer any cloud that is "acceptable" and has lower CO2 than current best
    for c in evaluated:
        if c["acceptable"] and c["co2_g"] < best_co2:
            best_where = f"cloud:{c['name']}"
            best_time = c["time_s"]
            best_co2 = c["co2_g"]

    # 6) Compute savings vs local baseline
    co2_saved = local_co2 - best_co2
    co2_saved_pct = (co2_saved / local_co2 * 100.0) if local_co2 > 0 else 0.0

    print("=== Decision ===")
    if best_where == "local":
        print("✅ Decision: LOCAL is better for this task.")
        print(f"(local {local_time:.3f}s, {local_co2:.4f} gCO2)")
    else:
        cloud_name = best_where.split(":", 1)[1]
        print(f"✅ Decision: CLOUD [{cloud_name}] is acceptable/better for this task.")
        print(f"Chosen: {best_where} with {best_time:.3f}s, {best_co2:.4f} gCO2")

    print()
    print("=== Savings vs local ===")
    print(f"CO₂ saved: {co2_saved:.4f} g ({co2_saved_pct:.1f}%)")
    print()

    print("For demo you can say:")
    if best_where == "local":
        print("  → 'Our engine chose to keep this task local because all cloud options would either emit much more CO₂ or be too slow.'")
    else:
        print(f"  → 'Our engine chose to offload this task to the {cloud_name} region based on lower CO₂ emissions and acceptable latency, saving {co2_saved_pct:.1f}% CO₂ compared to running locally.'")

    # 7) Log this run to CSV for future learning
    row = {
        "timestamp": time.time(),
        "local_time_s": local_time,
        "local_co2_g": local_co2,
        "local_ci_g_per_kwh": local_ci,
        "best_where": best_where,
        "best_time_s": best_time,
        "best_co2_g": best_co2,
        "co2_saved_g": co2_saved,
        "co2_saved_pct": co2_saved_pct,
    }
    # Add per-cloud info
    for c in evaluated:
        prefix = c["name"]
        row[f"{prefix}_time_s"] = c["time_s"]
        row[f"{prefix}_co2_g"] = c["co2_g"]
        row[f"{prefix}_ci_g_per_kwh"] = c["grid_ci"]
        row[f"{prefix}_acceptable"] = int(c["acceptable"])

    append_decision_log(row)


if __name__ == "__main__":
    main()
