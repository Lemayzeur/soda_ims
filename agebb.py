import re
import requests
from bs4 import BeautifulSoup
import pandas as pd

# lawrence County (Southwest Center) station
HEADER_URL = "http://agebb.missouri.edu/weather/stations/lawrence/headmtv.htm"
DATA_URL = "http://agebb.missouri.edu/weather/stations/lawrence/bull87tf.htm"

def fetch_pre_text(url):
    """Extracts raw string payload hidden inside HTML <pre> elements."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        pre_tag = soup.find('pre')
        return pre_tag.text if pre_tag else ""
    except Exception as e:
        print(f"Error accessing endpoint {url}: {e}")
        return ""

print("Fetching MU Extension weather records...")
raw_data_text = fetch_pre_text(DATA_URL)

if not raw_data_text:
    print("Failed to pull weather data matrix profiles.")
    exit()

# Splits lines across tabs/newlines and drops empty validation fields
lines = [line.strip() for line in raw_data_text.splitlines() if line.strip()]
parsed_rows = []

for line in lines:
    # Split across any length of whitespace variables (spaces or tabs)
    tokens = re.split(r'\s+', line)
    
    # Valid weather matrix lines must start with numeric Month and Day tokens
    if len(tokens) >= 10 and tokens[0].isdigit() and tokens[1].isdigit():
        month = int(tokens[0])
        day = int(tokens[1])
        
        # Build the baseline row mapping directly to MU Extension columns
        row = {
            "month": month,
            "day": day,
            "max_air_temp_f": float(tokens[2]),
            "min_air_temp_f": float(tokens[3]),
            "avg_rel_hum_pct": float(tokens[4]),
            "avg_bare_soil_temp_f": float(tokens[5]),
            "avg_wind_speed_mph": float(tokens[6]),
            "daily_solar_rad_mj_m2": float(tokens[7]),
            "daily_precip_mm_raw": float(tokens[8]), # Will convert below
            "accum_precip_ytd_raw": float(tokens[9])
        }
        parsed_rows.append(row)

parsed_rows = sorted(parsed_rows, key=lambda x: (x['month'], x['day']))

# Load into a Pandas DataFrame for validation and unit conversion arrays
df = pd.DataFrame(parsed_rows)

# Convert Temperatures: (°F - 32) * 5/9 = °C
df["max_air_temp_c"] = round((df["max_air_temp_f"] - 32) * 5 / 9, 2)
df["min_air_temp_c"] = round((df["min_air_temp_f"] - 32) * 5 / 9, 2)
df["avg_bare_soil_temp_c"] = round((df["avg_bare_soil_temp_f"] - 32) * 5 / 9, 2)

# Convert Wind Speed: MPH * 0.44704 = m/s
df["avg_wind_speed_m_s"] = round(df["avg_wind_speed_mph"] * 0.44704, 2)

# Convert Precipitation: Inches * 25.4 = mm
df["daily_precip_mm"] = round(df["daily_precip_mm_raw"] * 25.4, 2)

# Convert Solar Radiation: 
# MU reports in MJ/m² per day. ZENTRA reports raw intensity flux in W/m² (Watts = Joules/second).
# Later accumulate your hourly ZENTRA readings like this:
# (Sum of Hourly ZENTRA W/m² * 3600 seconds) / 1,000,000 = MJ/m² daily total value.
df["daily_solar_rad_mj_m2"] = df["daily_solar_rad_mj_m2"]

# Drop the unneeded imperial columns to keep the comparison matrix clean
columns_to_keep = [
    "month", "day", "max_air_temp_c", "min_air_temp_c", 
    "avg_rel_hum_pct", "avg_bare_soil_temp_c", 
    "avg_wind_speed_m_s", "daily_solar_rad_mj_m2", "daily_precip_mm"
]
df_final = df[columns_to_keep]

# save the data back down to a structured CSV
csv_filename = "extension_mt_vernon_clean.csv"
df_final.to_csv(csv_filename, index=False)

print(f"\n Success! Data exported to '{csv_filename}'. Ready for sensor comparison pipelines.")
print(df_final.head())
