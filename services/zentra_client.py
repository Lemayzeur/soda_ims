import random
import requests
from flask import current_app

from services.rate_limiter import wait_if_needed


def fetch_field_readings(field, start_date, end_date):
    """
    Returns a list like:
    [
        {
            "serial_number": "z6-31580",
            "battery_percent": 87,
            "ports": [
                {"port_number": 1, "value": 0.24, "error": False},
                {"port_number": 3, "value": 0.21, "error": False},
            ],
        },
        ...
    ]
    Respects each logger's include/exclude port mode.

    Falls back to generated demo data if DEMO_MODE is on, or if the
    real request fails, so the app stays fully testable without live
    hardware or a valid token.
    """
    results = []
    for logger in field.loggers:
        wanted_ports = _resolve_wanted_ports(logger)

        if current_app.config.get("DEMO_MODE") or not current_app.config.get("ZENTRA_TOKEN"):
            results.append(_demo_reading(logger, wanted_ports, field))
            continue

        try:
            results.append(_live_reading(logger, wanted_ports, start_date, end_date))
        except Exception as exc:
            current_app.logger.warning(f"Zentra fetch failed for {logger.serial_number}: {exc}")
            results.append(_demo_reading(logger, wanted_ports, field, forced_error=True))

    return results


def _resolve_wanted_ports(logger):
    ports = logger.get_ports()
    if logger.port_mode == "exclude":
        # Assumes a typical logger exposes ports 1-4; excludes the listed ones.
        all_ports = [1, 2, 3, 4]
        return [p for p in all_ports if p not in ports]
    return ports


def _demo_reading(logger, wanted_ports, field, forced_error=False):
    entry = {
        "serial_number": logger.serial_number,
        "battery_percent": round(random.uniform(15, 100), 0),
        "ports": [],
    }
    for p in wanted_ports:
        if forced_error or random.random() < 0.05:
            entry["ports"].append({"port_number": p, "value": None, "error": True})
        else:
            # bias values around the field's threshold so demo data looks plausible
            center = field.trigger_threshold + random.uniform(-0.02, 0.05)
            entry["ports"].append({
                "port_number": p,
                "value": round(max(0.05, center), 4),
                "error": False,
            })
    return entry


def _live_reading(logger, wanted_ports, start_date, end_date):
    token = current_app.config["ZENTRA_TOKEN"]
    base_url = current_app.config["ZENTRA_BASE_URL"]
    clean_token = token.replace("token ", "") if token.startswith("token ") else token

    headers = {"Authorization": f"Token {clean_token}", "Accept": "application/json"}
    params = {
        "device_sn": logger.serial_number,
        "start_date": start_date.strftime("%Y-%m-%d %H:%M"),
        "end_date": end_date.strftime("%Y-%m-%d %H:%M"),
        "location": "true",
    }

    # Waits here if needed, so we never exceed ZentraCloud's documented
    # 60 calls/minute account limit or 1 call/minute per-device limit.
    wait_if_needed(logger.serial_number)

    response = requests.get(f"{base_url}/get_readings", headers=headers, params=params, timeout=20)
    response.raise_for_status()
    json_data = response.json()
    data_block = json_data.get("data", {})

    water_content_list = data_block.get("Water Content", [])
    battery_list = data_block.get("Battery Percent", [])

    entry = {
        "serial_number": logger.serial_number, 
        "battery_percent": None, 
        "ports": []
    }

    if battery_list:
        readings = battery_list[0].get("readings", [])
        if readings:
            entry["battery_percent"] = readings[0].get("value")

    for reading_data in water_content_list:
        if "readings" not in reading_data:
            continue
        port_num = reading_data["metadata"]["port_number"]
        if port_num not in wanted_ports:
            continue
    
        latest = max(reading_data["readings"], key=lambda x: x['timestamp_utc'])        
        if latest.get("error_flag"):
            entry["ports"].append({"port_number": port_num, "value": None, "error": True})
        else:
            val = latest.get("value")
            if val is not None:
                entry["ports"].append({"port_number": port_num, "value": val, "error": False})

    return entry
