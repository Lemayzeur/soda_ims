from datetime import datetime, timedelta

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def get_forecast_template(field):
    """
    Placeholder forecast data — no real forecast source is connected yet.
    Values are left as null rather than faked, so the frontend honestly
    shows "—" instead of pretending to have real numbers.

    Swap the body of this function for a real call (e.g. Open-Meteo,
    NOAA NDFD) using field.latitude / field.longitude. Keep the same
    response shape so the frontend doesn't need to change.
    """
    today = datetime.now()
    days = []
    for i in range(7):
        day = today + timedelta(days=i)
        days.append({
            "date": day.strftime("%Y-%m-%d"),
            "day_label": "Today" if i == 0 else DAY_NAMES[day.weekday()],
            "high_f": None,
            "low_f": None,
            "rain_probability_pct": None,
            "eto_mm": None,  # to be computed once ETo integration is built
        })

    return {
        "field_id": field.id,
        "field_name": field.name,
        "latitude": field.latitude,
        "longitude": field.longitude,
        "is_template": True,
        "days": days,
    }
