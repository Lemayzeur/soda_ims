import requests
import os
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
import time
import traceback

load_dotenv()


config = {"token": os.getenv("ZENTRA_TOKEN"), "id": 11863}

base_uri = "https://zentracloud.com/api"
readings_path = "/v3/get_readings"
url = f"{base_uri}{readings_path}"

clean_token = config["token"].replace("token ", "") if config["token"].startswith("token ") else config["token"]
headers = {"Authorization": f"Token {clean_token}", "Accept": "application/json"}

END_DATE = datetime.strptime("2026-08-20 00:00", "%Y-%m-%d %H:%M") # datetime.now() 
START_DATE = datetime.strptime("2026-08-19 00:00", "%Y-%m-%d %H:%M")

# Setup initial query parameters
params = {
    "device_sn": "z6-30297",
    "start_date": START_DATE.strftime("%Y-%m-%d %H:%M:%S"),
    "location": "true",
    "per_page": 2000,  # Maximize page sizes to reduce API roundtrips
}
if END_DATE:
    params["end_date"] = END_DATE.strftime("%Y-%m-%d %H:%M:%S")

# Initialize master memory lists to accumulate raw data across all paginated pages
metrics_to_collect = [
    "Max Air Temperature", "Min Air Temperature", "Relative Humidity",
    "Soil Temperature", "Wind Speed", "Solar Radiation", "Precipitation"
]
raw_storage = {metric: [] for metric in metrics_to_collect}

# 1. Start Paginated API Requests Loop
next_url = url
is_first_page = True
page_counter = 0
MAX_PAGES_FAILSAFE = 50 # 3 days of 15-minute readings easily fit into 1 or 2 pages at 2000 records per page

print("Starting weather data download sequence from ZENTRA Cloud...")

try:
    i = 0
    while next_url:
        page_counter += 1

        # FAIL-SAFE 1: Terminate if pages exceed reasonable thresholds for a 3-day window
        if page_counter > MAX_PAGES_FAILSAFE:
            print(f"[FAIL-SAFE] Hard stop triggered: Script reached {MAX_PAGES_FAILSAFE} pages. Stopping loop to process current data.")
            break

        if is_first_page:
            # First request uses the baseline dictionary parameters
            response = requests.get(next_url, headers=headers, params=params)
            is_first_page = False
        else:
            print("Waiting 1 minute to respect API rate limits...")
            time.sleep(60)
            # Subsequent requests use the pre-built target URL provided by the API
            response = requests.get(next_url, headers=headers)
            
        response.raise_for_status()
        json_data = response.json()

        # Parse pagination dates to see if ZENTRA is ignoring your parameters
        pagination = json_data.get('pagination', {})
        page_start_str = pagination.get('page_start_date', '')

        if page_start_str:
            # Strip timezone offset from string context if necessary for comparison
            clean_date_str = page_start_str.split()[0] # Gets 'YYYY-MM-DD'
            current_page_date = datetime.strptime(clean_date_str, "%Y-%m-%d")
            
            # FAIL-SAFE 2: Terminate if the current API page date has drifted past your end target date
            if current_page_date > END_DATE:
                print(f"[FAIL-SAFE] Target date reached ({clean_date_str} is past {END_DATE.strftime('%Y-%m-%d')}). Breaking loop.")
                break

        data_block = json_data.get("data", json_data)
        
        # EXTENSION FIX: Extract data arrays directly from root dictionary levels
        for metric in metrics_to_collect:
            if metric in data_block and data_block[metric]:
                metric_entry = data_block[metric]
                readings = metric_entry[0].get('readings', []) if isinstance(metric_entry, list) else metric_entry.get('readings', [])
                # Access array zero layer safely to grab the readings list array
                raw_storage[metric].extend(readings)
                
        # Follow the link header array variable setup
        next_url =pagination.get("next_url")
        if next_url:
            i += 1
            print(f"Moving to next page layout: {next_url}")

    print("\n Download complete. Flattening and calculating weather metrics...")

    # 2. Flatten raw collected json entries into daily dataframes
    def process_metric_to_daily_series(raw_list, col_name, aggregation_type):
        if not raw_list:
            return pd.Series(dtype='float64')
        
        df = pd.DataFrame(raw_list)
        df['date'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')
        
        # Route logic patterns matching required daily aggregations
        if aggregation_type == "max":
            return df.groupby('date')['value'].max().rename(col_name)
        elif aggregation_type == "min":
            return df.groupby('date')['value'].min().rename(col_name)
        elif aggregation_type == "mean":
            return df.groupby('date')['value'].mean().rename(col_name)
        elif aggregation_type == "sum":
            return df.groupby('date')['value'].sum().rename(col_name)
        elif aggregation_type == "solar_sum":
            # Converts instant intensity readings vector to total daily mega-joules
            return (df.groupby('date')['value'].sum() * 0.0036).rename(col_name)

    # 3. Aggregate all weather metrics correctly
    series_max_temp = process_metric_to_daily_series(raw_storage["Max Air Temperature"], "max_temp", "max")
    series_min_temp = process_metric_to_daily_series(raw_storage["Min Air Temperature"], "min_temp", "min")
    series_rh       = process_metric_to_daily_series(raw_storage["Relative Humidity"], "rh", "mean")
    series_soil     = process_metric_to_daily_series(raw_storage["Soil Temperature"], "soil_temp", "mean")
    series_wind     = process_metric_to_daily_series(raw_storage["Wind Speed"], "wind", "mean")
    series_solar    = process_metric_to_daily_series(raw_storage["Solar Radiation"], "solar", "solar_sum")
    series_precip   = process_metric_to_daily_series(raw_storage["Precipitation"], "precip", "sum")

    # 4. Combine all weather dimensions cleanly into a unified data structure
    df_zentra_daily = pd.concat([
        series_max_temp, series_min_temp, series_rh, series_soil, series_wind, series_solar, series_precip
    ], axis=1).rename_axis('date').reset_index()

    # 5. Extract month and day integers to line up with the MU Extension CSV columns
    df_zentra_daily['date_obj'] = pd.to_datetime(df_zentra_daily['date'])
    df_zentra_daily['month'] = df_zentra_daily['date_obj'].dt.month
    df_zentra_daily['day'] = df_zentra_daily['date_obj'].dt.day

    # 6. Apply final structural layout schemas
    columns_to_keep = [
        "month", "day", "max_temp", "min_temp",  
        "rh", "soil_temp", "wind", "solar", "precip" 
    ]
    df_final_zentra = df_zentra_daily[columns_to_keep]
    
    # Fill any empty gaps with 0.0 for rain or drop them to maintain alignment
    df_final_zentra = df_final_zentra.dropna(subset=["max_temp", "min_temp"])

    output_filename = "zentra_weather_station_clean.csv"
    df_final_zentra.to_csv(output_filename, index=False)
    print(f"\n Success! Saved clean daily dataset containing {len(df_final_zentra)} entries to '{output_filename}'")

except Exception as err:
    traceback.print_exc()
    print(f"Pipeline failure: {err}")
