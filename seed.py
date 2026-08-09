from datetime import datetime, timedelta
from models import db, Field, Logger, AdminEmail
from services.tz_utils import local_naive_to_utc_naive

# Staggered by 15 minutes each, starting from a fixed reference point,
# so the six fields' recurring check cycles don't all land at once —
# see services/rate_limiter.py for why that matters.
# These are LOCAL wall-clock times (Central) — converted to UTC below
# before being stored, same path a real form submission goes through.
_BASE_START = datetime(2026, 8, 11, 6, 0, 0)  # first Tuesday 6:00 AM Central after seeding


def _staggered(offset_minutes):
    return _BASE_START + timedelta(minutes=offset_minutes)


SEED_FIELDS = [
    {
        # Real loggers/ports, matching your original script exactly.
        "name": "Vineyard", "trigger_threshold": 0.235, "target_vwc": 0.32,
        "soil_volume_m3": 1.002, "system_flow_lps": 0.00244,
        "latitude": 38.9472, "longitude": -92.3286,
        "start_date": _staggered(0),
        "timezone": "America/Chicago",
        "loggers": [
            {"serial_number": "z6-31580", "port_mode": "include", "ports": [1, 3]},
            {"serial_number": "z6-30299", "port_mode": "include", "ports": [1, 3]},
            {"serial_number": "z6-30297", "port_mode": "include", "ports": [2, 4]},
        ],
    },
    {
        # Placeholder loggers — swap for real serials when available.
        "name": "Organic Farm", "trigger_threshold": 0.229, "target_vwc": 0.32,
        "soil_volume_m3": 1.002, "system_flow_lps": 0.00244,
        "latitude": 38.9501, "longitude": -92.3310,
        "start_date": _staggered(15),
        "timezone": "America/Chicago",
        "loggers": [
            {"serial_number": "z6-00001-tbd", "port_mode": "include", "ports": [1, 3]},
            {"serial_number": "z6-00002-tbd", "port_mode": "include", "ports": [1, 3]},
        ],
    },
    {
        "name": "Lee Farm", "trigger_threshold": 0.210, "target_vwc": 0.30,
        "soil_volume_m3": 1.002, "system_flow_lps": 0.00244,
        "latitude": 38.9330, "longitude": -92.3400,
        "start_date": _staggered(30),
        "timezone": "America/Chicago",
        "loggers": [
            {"serial_number": "z6-00003-tbd", "port_mode": "include", "ports": [2, 4]},
        ],
    },
    {
        "name": "Blueberry Farm", "trigger_threshold": 0.230, "target_vwc": 0.33,
        "soil_volume_m3": 1.002, "system_flow_lps": 0.00244,
        "latitude": 38.9600, "longitude": -92.3150,
        "start_date": _staggered(45),
        "timezone": "America/Chicago",
        "loggers": [
            {"serial_number": "z6-00004-tbd", "port_mode": "include", "ports": [1, 2]},
        ],
    },
    {
        "name": "South Farm", "trigger_threshold": 0.240, "target_vwc": 0.32,
        "soil_volume_m3": 1.002, "system_flow_lps": 0.00244,
        "latitude": 38.9200, "longitude": -92.3500,
        "start_date": _staggered(60),
        "timezone": "America/Chicago",
        "loggers": [
            {"serial_number": "z6-00005-tbd", "port_mode": "include", "ports": [1, 2]},
        ],
    },
    {
        "name": "Bradford Farm", "trigger_threshold": 0.225, "target_vwc": 0.31,
        "soil_volume_m3": 1.002, "system_flow_lps": 0.00244,
        "latitude": 38.9050, "longitude": -92.3050,
        "start_date": _staggered(75),
        "timezone": "America/Chicago",
        "loggers": [
            {"serial_number": "z6-00006-tbd", "port_mode": "include", "ports": [1]},
        ],
    },
]

SEED_ADMINS = [
    "llgpp@missouri.edu",
    "mr6dz@missouri.edu",
    "jasmine.neupane@missouri.edu",
]


def seed_if_empty():
    if Field.query.first():
        return  # already seeded, don't duplicate

    for f in SEED_FIELDS:
        tz_name = f.get("timezone", "America/Chicago")
        field = Field(
            name=f["name"],
            trigger_threshold=f["trigger_threshold"],
            target_vwc=f["target_vwc"],
            soil_volume_m3=f["soil_volume_m3"],
            system_flow_lps=f["system_flow_lps"],
            timezone=tz_name,
            start_date=local_naive_to_utc_naive(f.get("start_date"), tz_name),
            latitude=f["latitude"],
            longitude=f["longitude"],
        )
        db.session.add(field)
        db.session.flush()  # so field.id is available for the loggers below

        for l in f["loggers"]:
            logger = Logger(field_id=field.id, serial_number=l["serial_number"], port_mode=l["port_mode"])
            logger.set_ports(l["ports"])
            db.session.add(logger)

    for email in SEED_ADMINS:
        db.session.add(AdminEmail(email=email))

    db.session.commit()