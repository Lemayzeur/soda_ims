def evaluate_field(field, logger_readings):
    """
    logger_readings: output of fetch_field_readings()
    Returns a dict describing the field's current status and, if
    irrigation is needed, how much water and how long to run.

    decision is one of:
      IRRIGATED  - at least one port is below threshold, water is needed
      OK         - all reporting ports are healthy
      PARTIAL    - some ports errored, but at least one good reading exists
      NO_DATA    - no usable readings at all
    """
    good_values = []
    below_threshold_count = 0
    error_count = 0
    battery_values = []

    for logger_entry in logger_readings:
        if logger_entry.get("battery_percent") is not None:
            battery_values.append(logger_entry["battery_percent"])
        for p in logger_entry["ports"]:
            if p["error"] or p["value"] is None:
                error_count += 1
                continue
            good_values.append(p["value"])
            if p["value"] < field.trigger_threshold:
                below_threshold_count += 1

    result = {
        "num_ports_reporting": len(good_values),
        "num_ports_below_threshold": below_threshold_count,
        "num_ports_error": error_count,
        "average_vwc": None,
        "min_vwc": None,
        "max_vwc": None,
        "battery_percent": min(battery_values) if battery_values else None,
        "decision": "NO_DATA",
        "vwc_deficit": None,
        "liters_needed": None,
        "runtime_hours": None,
        "runtime_minutes": None,
    }

    if not good_values:
        return result

    average_vwc = sum(good_values) / len(good_values)
    result["average_vwc"] = round(average_vwc, 4)
    result["min_vwc"] = round(min(good_values), 4)
    result["max_vwc"] = round(max(good_values), 4)

    if below_threshold_count > 0:
        vwc_deficit = field.target_vwc - average_vwc
        liters_needed = field.soil_volume_m3 * vwc_deficit * 1000
        runtime_seconds = liters_needed / field.system_flow_lps if field.system_flow_lps else 0

        hours = int(runtime_seconds // 3600)
        minutes = round((runtime_seconds % 3600) / 60)

        result.update({
            "decision": "IRRIGATED",
            "vwc_deficit": round(vwc_deficit, 4),
            "liters_needed": round(liters_needed, 2),
            "runtime_hours": hours,
            "runtime_minutes": minutes,
        })
    elif error_count > 0:
        result["decision"] = "PARTIAL"
    else:
        result["decision"] = "OK"

    return result
