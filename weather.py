import requests
import pandas as pd
import numpy as np

# 1. Target coordinates for Mount Vernon, Missouri
LATITUDE = 37.1031
LONGITUDE = -93.8183

# 2. Define your target validation window (adjust to match your ZENTRA chart data)
START_DATE = "2026-07-31"
END_DATE = "2026-08-01"

url = "https://api.open-meteo.com"
params = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
    "start_date": START_DATE,
    "end_date": END_DATE,
    "hourly": ["precipitation", 'precipitation_sum'],
    # "hourly": ["temperature_2m", "relative_humidity_2m", "vapor_pressure_deficit", "shortwave_radiation", "precipitation", 'precipitation_sum'],
    "timezone": "America/Chicago" # Matches local Missouri time profile
}

response = requests.get(url, params=params)
api_data = response.json()
print(api_data)

# 3. Compile reference station metrics into a DataFrame
df_reference = pd.DataFrame({
    'timestamp_local': api_data['hourly']['time'],
    'ref_temp_c': api_data['hourly']['temperature_2m'],
    'ref_rh_pct': api_data['hourly']['relative_humidity_2m'],
    'ref_vpd_kpa': api_data['hourly']['vapor_pressure_deficit'],
    'ref_solar_wm2': api_data['hourly']['shortwave_radiation'],
    'precipitation': api_data['hourly']['precipitation'],
})

# 4. Framework for calculation (Merge with your zentra dataframe on timestamp matching loops)
# df_merged = pd.merge(df_zentra, df_reference, on='timestamp_local')
# error_margin = np.mean(np.abs(df_merged['zentra_temp'] - df_merged['ref_temp_c']))
print(df_reference.head())
