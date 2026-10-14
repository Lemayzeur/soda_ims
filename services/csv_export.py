import csv
import io


def irrigation_logs_to_csv(logs):
    output = io.StringIO()
    fieldnames = [
        "timestamp", "field_name", "decision", "average_vwc", "min_vwc", "max_vwc",
        "num_ports_reporting", "num_ports_below_threshold", "num_ports_error",
        "trigger_threshold", "target_vwc", "soil_volume_m3", "system_flow_lps",
        "vwc_deficit", "liters_needed", "runtime_hours", "runtime_minutes",
        "battery_percent", "raw_ports_json",  # <-- NEW: per-logger, per-port snapshot, needed for UAV correlation,
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for log in logs:
        d = log.to_dict()
        row = {k: d.get(k, "") for k in fieldnames if k != "raw_ports_json"}
        row["raw_ports_json"] = log.raw_ports_json or ""  # raw string, not the parsed dict
        writer.writerow(row)
    return output.getvalue()


def fields_to_csv(fields):
    output = io.StringIO()
    fieldnames = [
        "name", "trigger_threshold", "target_vwc", "soil_volume_m3",
        "system_flow_lps", "latitude", "longitude", "loggers",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for f in fields:
        logger_summary = "; ".join(
            f"{l.serial_number} ({l.port_mode}: {','.join(str(p) for p in l.get_ports())})"
            for l in f.loggers
        )
        writer.writerow({
            "name": f.name,
            "trigger_threshold": f.trigger_threshold,
            "target_vwc": f.target_vwc,
            "soil_volume_m3": f.soil_volume_m3,
            "system_flow_lps": f.system_flow_lps,
            "latitude": f.latitude,
            "longitude": f.longitude,
            "loggers": logger_summary,
        })
    return output.getvalue()


def alerts_to_csv(alerts):
    output = io.StringIO()
    fieldnames = ["created_at", "field_name", "alert_type", "message", "sent_to"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for a in alerts:
        d = a.to_dict()
        writer.writerow({
            "created_at": d["created_at"],
            "field_name": d["field_name"],
            "alert_type": d["alert_type"],
            "message": d["message"],
            "sent_to": "; ".join(d["sent_to"]),
        })
    return output.getvalue()
