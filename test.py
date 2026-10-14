from datetime import datetime, timedelta
import time
import requests
import os
import csv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

 # Constants
ADMIN_EMAILS = [
    "llgpp@missouri.edu",
    "mr6dz@missouri.edu",
    # "jasmine.neupane@missouri.edu",
]
 
FIELD_NAME = "Vineyard Farm"

SOIL_VOLUME = 2.74 * 1.22 * 0.30       # 1.002 m³ (Block volume)
TARGET_VWC = 0.32                      # Ideal Field Capacity
TRIGGER_THRESHOLD = 0.229              # Your new threshold set to 0.229
SYSTEM_FLOW_LPS = 0.00244              # Emitters total water output (Liters per second)

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

LOGGERS = [
    {"sn": "z6-31580", "ports": [1, 3]}, 
    {"sn": "z6-30299", "ports": [1, 3]}, 
    {"sn": "z6-30297", "ports": [2, 4]},
]

END_DATE = datetime.now() #datetime.strptime("2026-08-05 13:15", "%Y-%m-%d %H:%M")
START_DATE = END_DATE - timedelta(days=15) # "2026-08-02 00:00"

# datetime.strptime(date_string, "%Y-%m-%d %H:%M")

LOG_CSV_PATH = "irrigation_log.csv"
 
CSV_FIELDS = [
    "timestamp",
    "field_name",
    "decision", # IRRIGATED or NO_ACTION
    "average_vwc",
    "min_port_vwc",
    "max_port_vwc",
    "num_ports_reporting",
    "num_ports_below_threshold",
    "num_ports_error",
    "trigger_threshold",
    "target_vwc",
    "soil_volume_m3",
    "system_flow_lps",
    "vwc_deficit",
    "liters_needed",
    "runtime_hours",
    "runtime_minutes",
    "runtime_total_minutes",
]

def summarize_res(res):
    """
    Pulls quick stats out of the structured res list, used both for
    the email body and for the CSV log row.
    """
    all_values = [p["value"] for logger in res for p in logger["ports"]]
    num_below = sum(
        1 for logger in res for p in logger["ports"] if p["below_threshold"]
    )
    num_errors = sum(len(logger.get("errors", [])) for logger in res)
 
    return {
        "min_port_vwc": round(min(all_values), 4) if all_values else "",
        "max_port_vwc": round(max(all_values), 4) if all_values else "",
        "num_ports_reporting": len(all_values),
        "num_ports_below_threshold": num_below,
        "num_ports_error": num_errors,
    }
 
 
def log_irrigation_event_to_csv(decision, res, average_vwc=None, vwc_deficit=None, liters_needed=None, runtime_hours=None, runtime_minutes=None):
    """
    Appends one row per check (irrigated or not) to LOG_CSV_PATH.
    Writes the header only the first time the file is created, so it's
    safe to call this every run without wiping past history.
 
    Keeping a row for NO_ACTION checks too (not just irrigation events)
    matters here — without them you can't tell "the field needed 0 L"
    from "we never checked," which is exactly the comparison you'd want
    against a conventional calendar-based irrigation schedule.
    """
    file_exists = os.path.isfile(LOG_CSV_PATH)
    stats = summarize_res(res)
 
    row = {
        "timestamp": END_DATE.strftime("%Y-%m-%d %H:%M:%S"),
        "field_name": FIELD_NAME,
        "decision": decision,
        "average_vwc": round(average_vwc, 4) if average_vwc is not None else "",
        "min_port_vwc": stats["min_port_vwc"],
        "max_port_vwc": stats["max_port_vwc"],
        "num_ports_reporting": stats["num_ports_reporting"],
        "num_ports_below_threshold": stats["num_ports_below_threshold"],
        "num_ports_error": stats["num_ports_error"],
        "trigger_threshold": TRIGGER_THRESHOLD,
        "target_vwc": TARGET_VWC,
        "soil_volume_m3": round(SOIL_VOLUME, 4),
        "system_flow_lps": SYSTEM_FLOW_LPS,
        "vwc_deficit": round(vwc_deficit, 4) if vwc_deficit is not None else "",
        "liters_needed": round(liters_needed, 2) if liters_needed is not None else "",
        "runtime_hours": runtime_hours if runtime_hours is not None else "",
        "runtime_minutes": runtime_minutes if runtime_minutes is not None else "",
        "runtime_total_minutes": (
            round(runtime_hours * 60 + runtime_minutes, 1)
            if runtime_hours is not None and runtime_minutes is not None
            else ""
        ),
    }
 
    try:
        with open(LOG_CSV_PATH, mode="a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
        print(f"📝 Logged {decision} event to {LOG_CSV_PATH}")
    except Exception as e:
        print(f"❌ Failed to write CSV log: {e}")
 
  
def build_readings_block(res):
    """
    Turns the structured `res` list into a readable, per-logger,
    per-port text block for the email body.
    """
    lines = []
    for logger in res:
        lines.append(f"Logger: {logger['sn']}  ({logger['name']})")
        lines.append(f"  Location: {logger['location']}")
        lines.append(f"  Battery: {logger.get('battery', 'N/A')}")
 
        for p in logger["ports"]:
            flag = " ⚠️ BELOW THRESHOLD" if p["below_threshold"] else ""
            lines.append(f"  Port #{p['port_number']}: {p['value']} m3/m3{flag}")
 
        for err_port in logger.get("errors", []):
            lines.append(f"  Port #{err_port}: ⚠️ SENSOR ERROR — no reading")
 
        lines.append("")  # blank line between loggers
 
    return "\n".join(lines)

 
def process_average_sensor_payload(all_device_readings, res=None):
    if res is None:
        res = []
    
    if not all_device_readings:
        print("❌ No valid soil moisture data collected from any device. Aborting calculation.")
        return

    # loggers = all_device_readings.keys() # dict_keys(['z6-31580', 'z6-30299'])
    # readings = all_device_readings.values() # dict_values([[0.231, 0.223], [0.231, 0.223]])

    # if any of the readings is below the trigger_threshold
    any_below_threshold = any(val < TRIGGER_THRESHOLD for val in all_device_readings)

    # Check if the average moisture dropped to or below the trigger point
    # if average_vwc <= TRIGGER_THRESHOLD:

    if any_below_threshold: 
        # ALERT, IRRIGATION NEEDED
        # Calculate the average VWC across all active loggers
        average_vwc = sum(all_device_readings) / len(all_device_readings)
        print(f"\n📊 Summary Across {len(all_device_readings)} Loggers:")
        print(f"    -> Calculated Average Soil Moisture: {round(average_vwc, 4)} m³/m³")

        print("⚠️ Average soil moisture is below threshold! Calculating irrigation need...")
        
        # Step A: Find the VWC deficit based on the average
        vwc_deficit = TARGET_VWC - average_vwc
        
        # Step B: Calculate total liters of water missing from the soil block
        liters_needed = SOIL_VOLUME * vwc_deficit * 1000
        
        # Step C: Calculate how many hours the system must run
        runtime_seconds = liters_needed / SYSTEM_FLOW_LPS

        hours = int(runtime_seconds // 3600)
        minutes = round((runtime_seconds % 3600) / 60)


        log_irrigation_event_to_csv(
            decision="IRRIGATED",
            res=res,
            average_vwc=average_vwc,
            vwc_deficit=vwc_deficit,
            liters_needed=liters_needed,
            runtime_hours=hours,
            runtime_minutes=minutes,
        )

        # Call your notification email system
        trigger_email_notification(round(average_vwc, 3), hours, minutes, res)
    else:
        print("✅ Average soil moisture is healthy. No irrigation needed.")

        average_vwc = sum(all_device_readings) / len(all_device_readings)
        log_irrigation_event_to_csv(
            decision="NO_ACTION",
            res=res,
            average_vwc=average_vwc,
        )

def trigger_email_notification(vwc, hours, minutes, res):
    subject = f"[SoDA Alert] {FIELD_NAME} needs irrigation — {hours}h {minutes}m"

    readings_block = build_readings_block(res)

    body = f"""Irrigation Alert — {FIELD_NAME}
 
Date/Time checked: {END_DATE.strftime("%A, %B %d, %Y %I:%M %p")}
Average soil moisture (VWC): {round(vwc, 4)} m3/m3
Trigger threshold: {TRIGGER_THRESHOLD} m3/m3
Emitters total water output: {SYSTEM_FLOW_LPS} L/s
 
Recommended irrigation runtime: {hours} hour(s) {minutes} minute(s)
 
Individual sensor readings:
{readings_block}
This is an automated message from the SoDA irrigation monitoring system.
"""
 
    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = ", ".join(ADMIN_EMAILS)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
 
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, ADMIN_EMAILS, msg.as_string())
        print(f"📧 Email sent to {', '.join(ADMIN_EMAILS)}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

# 1. Configuration Setup
resp = {
    "token": os.getenv("ZENTRA_TOKEN"),
    "id": 11863
}

config = {"token": resp['token'], "id": 11863}

base_uri = "https://zentracloud.com/api"
readings_path = "/v3/get_readings"
url = f"{base_uri}{readings_path}"

clean_token = config["token"].replace("token ", "") if config["token"].startswith("token ") else config["token"]
headers = {"Authorization": f"Token {clean_token}", "Accept": "application/json"}

# Storage list for the newest reading from each valid logger
collected_vwc_values = []

res = []

# 2. Main API Harvesting Loop
for index, log_data in enumerate(LOGGERS):
    logger_sn = log_data['sn']
    ports = log_data['ports']
    print(f"\n📡 Requesting data for logger [{index + 1}/{len(LOGGERS)}]: {logger_sn}")
    
    params = {
        "device_sn": logger_sn,
        "start_date": START_DATE.strftime("%Y-%m-%d %H:%M:%S"),
        "location": "true",
    }
    if END_DATE:
        params["end_date"] = END_DATE.strftime("%Y-%m-%d %H:%M:%S")

    try:
        response = requests.get(url, headers=headers, params=params)

        # Handle Rate Limiting (Error 429) dynamically
        if response.status_code == 429:
            error_detail = response.json().get("detail", "")
            print(f"⚠️ Rate limit encountered: {error_detail}")
            wait_time = 62  # Standard safety buffer fallback
            
            words = error_detail.split()
            if "expires" in words and "in" in words:
                try:
                    wait_time = int(words[words.index("in") + 1]) + 2
                except (ValueError, IndexError):
                    pass
                    
            print(f"⏳ Pausing script execution for {wait_time} seconds before retrying this logger...")
            time.sleep(wait_time)
            
            # Re-execute the request for this specific logger after sleep
            response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            json_data = response.json()
            data_block = json_data.get("data", {})
            water_content_list = data_block.get("Water Content", [])
            battery_list = data_block.get("Battery Percent", [])

            meta = water_content_list[0].get("metadata", {})
            entry = {
                "sn": logger_sn,
                "name": meta.get("device_name", logger_sn),
                "location": f"{meta.get('latitude', 'N/A')}, {meta.get('longitude', 'N/A')}",
                "battery": None,
                "ports": [],
                "errors": [],
            }

            if battery_list:
                battery_readings = battery_list[0].get("readings", [])
                if battery_readings:
                    latest_battery = battery_readings[0].get("value")
                    if latest_battery is not None:
                        entry["battery"] = f"{round(latest_battery)}%"

            # Get all the readings for the water content
            port_readings = []
            for reading_data in water_content_list:
                if "readings" not in reading_data:
                    continue 

                # get the port number
                port_num = reading_data['metadata']['port_number']
                # if the port number is not included in targeted ports, pass
                if port_num not in ports:
                    continue 
                
                latest_reading = reading_data["readings"][0]
                
                # Check for errors on this specific sensor probe
                if latest_reading.get("error_flag"):
                    print(f"❌ Skipping {logger_sn} in Port {port_num}: Hardware reporting error flag.")
                    entry["errors"].append(port_num)
                    continue


                val = latest_reading.get("value")
                if val is not None:
                    print(f"✅ 'Water Content' value of {logger_sn} for Port {port_num}: {val}")
                    #collected_vwc_values.append(val)
                    port_readings.append(val)
                    collected_vwc_values.append(val)

                    entry['ports'].append({
                        "port_number": port_num,
                        "value": val,
                        "below_threshold": val < TRIGGER_THRESHOLD,
                    })


            if port_readings or entry["errors"]:
                # avg_val = round(sum(port_readings) / len(port_readings), 3)
                # collected_vwc_values[logger_sn] = port_readings
                # collected_vwc_values += port_readings
                # print(f"✅ Extracted moisture value from {logger_sn}: {port_readings}")
                res.append(entry)
            else:
                print(f"⚠️ Values for 'Water Content' missing for logger {logger_sn}")
        else:
            print(f"❌ Failed connection to logger {logger_sn}. Status code: {response.status_code}")

    except Exception as err:
        print(f"❌ Networking error encountered with logger {logger_sn}: {err}")

    # Enforce a 62-second sleep between requests to avoid hitting the 429 limit on the next loop
    # if index < len(LOGGERS) - 1:
    #     print("⏳ Respecting 1-minute rate limits. Sleeping for 62 seconds before checking the next device...")
    #     time.sleep(62)

# 3. Compute Averages and Process Triggers
process_average_sensor_payload(collected_vwc_values, res)
