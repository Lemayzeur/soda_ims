import math 

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
    mode = getattr(field, "evaluation_mode", "section_average")

    good_values = []
    below_threshold_count = 0
    error_count = 0
    battery_values = []
    port_decisions = []

    for logger_entry in logger_readings:
        if logger_entry.get("battery_percent") is not None:
            battery_values.append(logger_entry["battery_percent"])

        for port in logger_entry["ports"]:
            port_number = port["port_number"]
            value = port.get("value")
            has_error = port.get("error", False) or value is None

            mapping = {}

            if has_error:
                error_count += 1

                if mode == "individual_port":
                    port_decisions.append({
                        "serial_number": logger_entry["serial_number"],
                        "port_number": port_number,
                        "pot_number": port_number,
                        # "pot_number": mapping.get("pot_number"),
                        "valve": port_number,
                        "vwc": None,
                        "status": "SENSOR_ERROR",
                        "needs_irrigation": False,
                        "liters_needed": None,
                        "runtime_seconds": None,
                        "seconds": None,
                    })

                continue

            good_values.append(value)

            if value < field.trigger_threshold:
                below_threshold_count += 1

            if mode == "individual_port":
                # Use an explicit mapping when configured.
                # Fall back to port = pot = valve for the greenhouse setup.

                pot_number = mapping.get("pot_number", port_number)
                valve = mapping.get("valve", port_number)

                needs_irrigation = value < field.trigger_threshold

                liters_needed = None
                runtime_seconds = None

                soil_volume = field.soil_volume_m3
                flow_lps = field.system_flow_lps
                target_vwc = field.target_vwc

                if (
                    needs_irrigation
                    and soil_volume is not None
                    and flow_lps is not None
                    and flow_lps > 0
                    and target_vwc is not None
                ):
                    # Calculate the deficit from this pot's VWC
                    # to the target VWC, not the average VWC.
                    vwc_deficit = max(target_vwc - value, 0)

                    liters_needed = (
                        soil_volume * vwc_deficit * 1000
                    )

                    # Round UP to a whole second so the requested
                    # runtime does not undershoot the calculation.
                    runtime_seconds = math.ceil(
                        liters_needed / flow_lps
                    )

                port_decisions.append({
                    "serial_number": logger_entry["serial_number"],
                    "port_number": port_number,
                    "pot_number": pot_number,
                    "valve": valve,
                    "vwc": round(value, 4),
                    "status": (
                        "IRRIGATION_NEEDED"
                        if needs_irrigation else "OK"
                    ),
                    "needs_irrigation": needs_irrigation,
                    "liters_needed": (
                        round(liters_needed, 3)
                        if liters_needed is not None else None
                    ),
                    "runtime_seconds": runtime_seconds,
                    "seconds": runtime_seconds,
                })

    result = {
        "evaluation_mode": mode,
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
        "port_decisions": port_decisions,
    }

    if not good_values:
        return result

    average_vwc = sum(good_values) / len(good_values)

    result.update({
        "average_vwc": round(average_vwc, 4),
        "min_vwc": round(min(good_values), 4),
        "max_vwc": round(max(good_values), 4),
    })

    if below_threshold_count > 0:
        result["decision"] = "IRRIGATED"

        # Only calculate a field-wide water amount in averaging mode.
        if mode == "section_average":

            vwc_deficit = field.target_vwc - average_vwc
            liters_needed = field.soil_volume_m3 * vwc_deficit * 1000
            runtime_seconds = (
                liters_needed / field.system_flow_lps 
                if field.system_flow_lps else 0
            )

            result.update({
                "vwc_deficit": round(vwc_deficit, 4),
                "liters_needed": round(liters_needed, 2),
                "runtime_hours": int(runtime_seconds // 3600),
                "runtime_minutes": round((runtime_seconds % 3600) / 60),
            })
    elif error_count > 0:
        result["decision"] = "PARTIAL"
    else:
        result["decision"] = "OK"

    return result
