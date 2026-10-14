import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import current_app


def send_irrigation_alert_email(field, evaluation, logger_readings, admin_emails, timestamp):
    subject = (
        f"[SoDA Alert] {field.name} needs irrigation — "
        f"{evaluation['runtime_hours']}h {evaluation['runtime_minutes']}m"
    )
    body = f"""Irrigation Alert — {field.name}

Date/Time checked: {timestamp.strftime("%A, %B %d, %Y %I:%M %p")}
Average soil moisture (VWC): {evaluation['average_vwc']} m3/m3
Trigger threshold: {field.trigger_threshold} m3/m3
Ports below threshold: {evaluation['num_ports_below_threshold']} of {evaluation['num_ports_reporting']}

Recommended irrigation runtime: {evaluation['runtime_hours']} hour(s) {evaluation['runtime_minutes']} minute(s)
Estimated water needed: {evaluation['liters_needed']} L

Individual sensor readings:
{_format_readings_block(logger_readings, field.trigger_threshold)}
This is an automated message from the SoDA irrigation monitoring system.
"""
    return _send(subject, body, admin_emails)


def send_sensor_warning_email(field, evaluation, logger_readings, admin_emails, message):
    subject = f"[SoDA Warning] {field.name} — sensor issue detected"
    body = f"""Sensor Warning — {field.name}

{message}

Individual sensor readings:
{_format_readings_block(logger_readings, field.trigger_threshold)}
This is an automated message from the SoDA irrigation monitoring system.
"""
    return _send(subject, body, admin_emails)


def _send(subject, body, admin_emails):
    if not admin_emails:
        current_app.logger.info("No admin emails configured — skipping email send.")
        return False

    gmail_address = current_app.config.get("GMAIL_ADDRESS")
    gmail_password = current_app.config.get("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_password:
        current_app.logger.warning("Gmail credentials not set in .env — email not sent.")
        return False

    msg = MIMEMultipart()
    msg["From"] = gmail_address
    msg["To"] = ", ".join(admin_emails)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_password)
            server.sendmail(gmail_address, admin_emails, msg.as_string())
        return True
    except Exception as exc:
        current_app.logger.error(f"Failed to send email: {exc}")
        return False


def _format_readings_block(logger_readings, threshold):
    lines = []
    for logger_entry in logger_readings:
        lines.append(f"Logger: {logger_entry['serial_number']}")
        battery = logger_entry.get("battery_percent")
        lines.append(f"  Battery: {battery}%" if battery is not None else "  Battery: N/A")
        for p in logger_entry["ports"]:
            if p["error"] or p["value"] is None:
                lines.append(f"  Port #{p['port_number']}: SENSOR ERROR")
            else:
                flag = " (⚠️ BELOW THRESHOLD)" if p["value"] < threshold else ""
                lines.append(f"  Port #{p['port_number']}: {p['value']} m3/m3{flag}")
        lines.append("")
    return "\n".join(lines)
