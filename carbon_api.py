# carbon_api.py
import time
import requests

# 🔑 Your ElectricityMaps token (the one that works for IN-WE)
# 👉 REPLACE THIS WITH YOUR REAL TOKEN, KEEP IT SECRET, DO NOT COMMIT TO GITHUB
ELECTRICITYMAPS_TOKEN = "pQuBak7CvdQIIS4uKla5"

_CACHE = {}
CACHE_SECONDS = 600  # 10 minutes


def _fallback_for_zone(zone: str) -> float:
    """Return a conservative carbon intensity fallback for the given zone."""
    zone = zone.upper()
    if zone.startswith("IN"):
        return 700.0  # dirtier grid assumption for India
    return 400.0      # generic fallback


def _fetch_from_api(zone: str) -> float:
    """Internal helper: call ElectricityMaps for zones your key supports."""
    zone = zone.upper()
    now = time.time()

    # Cache
    if zone in _CACHE:
        ts, val = _CACHE[zone]
        if now - ts < CACHE_SECONDS:
            return val

    url = f"https://api.electricitymap.org/v3/carbon-intensity/latest?zone={zone}"
    headers = {"auth-token": ELECTRICITYMAPS_TOKEN}

    print(f"[carbon_api] Requesting carbon intensity for zone={zone}")
    try:
        r = requests.get(url, headers=headers, timeout=5)
    except requests.exceptions.Timeout:
        fallback = _fallback_for_zone(zone)
        print(f"[carbon_api] Timeout for zone={zone}, using fallback {fallback} gCO2/kWh")
        _CACHE[zone] = (now, fallback)
        return fallback
    except requests.exceptions.RequestException as exc:
        fallback = _fallback_for_zone(zone)
        print(f"[carbon_api] Request error for zone={zone}: {exc}. Using fallback {fallback} gCO2/kWh")
        _CACHE[zone] = (now, fallback)
        return fallback

    if not r.ok:
        # Print once for debugging
        print(f"[carbon_api] ERROR {r.status_code} for zone={zone}: {r.text[:200]}")
        fallback = _fallback_for_zone(zone)
        print(f"[carbon_api] Using fallback {fallback} gCO2/kWh for zone={zone}")
        _CACHE[zone] = (now, fallback)
        return fallback

    try:
        data = r.json()
        val = float(data["carbonIntensity"])
    except (ValueError, KeyError, TypeError) as exc:
        fallback = _fallback_for_zone(zone)
        print(f"[carbon_api] Invalid payload for zone={zone}: {exc}. Using fallback {fallback} gCO2/kWh")
        _CACHE[zone] = (now, fallback)
        return fallback

    _CACHE[zone] = (now, val)
    print(f"[carbon_api] zone={zone}, carbonIntensity={val} gCO2/kWh")
    return val


def get_zone_carbon_g_per_kwh(zone: str) -> float:
    """
    Public function used by the rest of your code.

    - Uses live ElectricityMaps data for IN-WE (your subscription region).
    - Uses a realistic fixed value for Stockholm region (SE-SE4), since your key
      doesn't have access to it.
    - Returns a reasonable fallback for any other zone.
    """
    zone = zone.upper()

    # ✅ Live API for your real region (Western India)
    if zone in ("IN-WE", "IN", "IN-WEST"):
        return _fetch_from_api("IN-WE")

    # ✅ Fixed value for Sweden / Stockholm (AWS eu-north-1)
    if zone in ("SE-SE4", "SE-SE3", "SE"):
        # Sweden approx 20–50 gCO2/kWh, pick 50 for demo
        return 50.0

    # 🔁 Fallback for anything else
    return 400.0
