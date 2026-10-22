import json
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

from services.tz_utils import utc_naive_to_local_iso, DEFAULT_TIMEZONE

db = SQLAlchemy()

class Field(db.Model):
    __tablename__ = "fields"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    trigger_threshold = db.Column(db.Float, nullable=False, default=0.229)
    target_vwc = db.Column(db.Float, nullable=False, default=0.32)
    soil_volume_m3 = db.Column(db.Float, nullable=False, default=1.002)
    system_flow_lps = db.Column(db.Float, nullable=False, default=0.00244)
    check_frequency_days = db.Column(db.Integer, nullable=False, default=5)
    # When this field's recurring check cycle should first begin. Lets
    # different fields be offset from each other (e.g. Field A starts
    # Monday 6am, Field B starts Monday 6:10am) so their scheduled
    # checks don't all fire in the same instant and stack up API calls.
    start_date = db.Column(db.DateTime, nullable=True)
    # IANA timezone name (e.g. "America/Chicago"). Every datetime in
    # this table is stored as naive UTC — this is only used to convert
    # to/from that field's local wall-clock time at the edges (form
    # input and display), see services/tz_utils.py.
    timezone = db.Column(db.String(60), nullable=False, default=DEFAULT_TIMEZONE)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # to know whether to evaluate all the ports in once, or individually
    evaluation_mode = db.Column(db.String(30), nullable=False, default="section_average") # section_average OR individual_port
    
    loggers = db.relationship(
        "Logger", backref="field", cascade="all, delete-orphan", lazy=True
    )
    irrigation_logs = db.relationship(
        "IrrigationLog", backref="field", cascade="all, delete-orphan", lazy=True
    )
    alerts = db.relationship(
        "AlertLog", backref="field", cascade="all, delete-orphan", lazy=True
    )
    

    def next_check_due(self):
        """
        Computes the next scheduled check time from start_date and
        check_frequency_days. Purely informational right now (the
        scheduler doesn't yet act on this per-field) — but it's what
        a future per-field scheduler would use to decide when to run,
        and it's useful on the dashboard as-is.
        """
        if not self.start_date:
            return None

        now = datetime.utcnow()
        if self.start_date >= now:
            return self.start_date

        interval = timedelta(days=self.check_frequency_days or 5)
        elapsed = now - self.start_date
        cycles_passed = elapsed // interval
        return self.start_date + (cycles_passed + 1) * interval

    def to_dict(self, include_loggers=True):
        tz_name = self.timezone or DEFAULT_TIMEZONE
        next_due = self.next_check_due()
        data = {
            "id": self.id,
            "name": self.name,
            "evaluation_mode": self.evaluation_mode,
            "trigger_threshold": self.trigger_threshold,
            "target_vwc": self.target_vwc,
            "soil_volume_m3": self.soil_volume_m3,
            "system_flow_lps": self.system_flow_lps,
            "check_frequency_days": self.check_frequency_days,
            "timezone": tz_name,
            # Raw UTC (source of truth) alongside a local-time version
            # for display, so the frontend never has to guess a zone.
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "start_date_local": utc_naive_to_local_iso(self.start_date, tz_name),
            "next_check_due": next_due.isoformat() if next_due else None,
            "next_check_due_local": utc_naive_to_local_iso(next_due, tz_name),
            "latitude": self.latitude,
            "longitude": self.longitude,
        }
        if include_loggers:
            data["loggers"] = [l.to_dict() for l in self.loggers]
        return data

class Logger(db.Model):
    __tablename__ = "loggers"

    id = db.Column(db.Integer, primary_key=True)
    field_id = db.Column(db.Integer, db.ForeignKey("fields.id"), nullable=False)
    serial_number = db.Column(db.String(60), nullable=False)
    port_mode = db.Column(db.String(10), nullable=False, default="include")  # include|exclude
    ports = db.Column(db.Text, nullable=False, default="[]")  # JSON list of ints
    port_map = db.Column(db.JSON, nullable=True, default=dict)

    def get_ports(self):
        try:
            return json.loads(self.ports)
        except (TypeError, ValueError):
            return []

    def set_ports(self, ports_list):
        self.ports = json.dumps([int(p) for p in ports_list])

    def to_dict(self):
        return {
            "id": self.id,
            "field_id": self.field_id,
            "serial_number": self.serial_number,
            "port_mode": self.port_mode,
            "ports": self.get_ports(),
        }

class AdminEmail(db.Model):
    __tablename__ = "admin_emails"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "email": self.email}

class AlertLog(db.Model):
    __tablename__ = "alert_logs"

    id = db.Column(db.Integer, primary_key=True)
    field_id = db.Column(db.Integer, db.ForeignKey("fields.id"), nullable=False)
    alert_type = db.Column(db.String(30), nullable=False)  # IRRIGATION | SENSOR_WARNING
    message = db.Column(db.Text, nullable=False)
    sent_to = db.Column(db.Text, nullable=False, default="[]")  # JSON list
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        try:
            sent_to = json.loads(self.sent_to)
        except (TypeError, ValueError):
            sent_to = []
        tz_name = self.field.timezone if self.field else DEFAULT_TIMEZONE
        return {
            "id": self.id,
            "field_id": self.field_id,
            "field_name": self.field.name if self.field else None,
            "alert_type": self.alert_type,
            "message": self.message,
            "sent_to": sent_to,
            "created_at": self.created_at.isoformat(),
            "created_at_local": utc_naive_to_local_iso(self.created_at, tz_name),
        }

class IrrigationLog(db.Model):
    __tablename__ = "irrigation_logs"

    id = db.Column(db.Integer, primary_key=True)
    field_id = db.Column(db.Integer, db.ForeignKey("fields.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    decision = db.Column(db.String(20), nullable=False)  # IRRIGATED | OK | PARTIAL | NO_DATA
    average_vwc = db.Column(db.Float, nullable=True)
    min_vwc = db.Column(db.Float, nullable=True)
    max_vwc = db.Column(db.Float, nullable=True)
    num_ports_reporting = db.Column(db.Integer, default=0)
    num_ports_below_threshold = db.Column(db.Integer, default=0)
    num_ports_error = db.Column(db.Integer, default=0)
    trigger_threshold = db.Column(db.Float, nullable=True)
    target_vwc = db.Column(db.Float, nullable=True)
    soil_volume_m3 = db.Column(db.Float, nullable=True)
    system_flow_lps = db.Column(db.Float, nullable=True)
    vwc_deficit = db.Column(db.Float, nullable=True)
    liters_needed = db.Column(db.Float, nullable=True)
    runtime_hours = db.Column(db.Integer, nullable=True)
    runtime_minutes = db.Column(db.Integer, nullable=True)
    runtime_seconds = db.Column(db.Integer, nullable=True)
    battery_percent = db.Column(db.Float, nullable=True)
    raw_ports_json = db.Column(db.Text, nullable=True)  # JSON snapshot of per-port readings

    command_id = db.Column(db.String(100), unique=True, nullable=True, index=True)
    pot_number = db.Column(db.Integer, nullable=True)
    valve = db.Column(db.Integer, nullable=True)

    execution_status = db.Column(
        db.String(30), nullable=True, default="pending"
    )
    execution_message = db.Column(db.String(255), nullable=True)
    execution_started_at = db.Column(db.DateTime, nullable=True)
    execution_completed_at = db.Column(db.DateTime, nullable=True)

    actual_liters = db.Column(db.Float, nullable=True)

    def to_dict(self):
        raw_ports = []
        if self.raw_ports_json:
            try:
                raw_ports = json.loads(self.raw_ports_json)
            except (TypeError, ValueError):
                raw_ports = []
        tz_name = self.field.timezone if self.field else DEFAULT_TIMEZONE
        return {
            "id": self.id,
            "field_id": self.field_id,
            "field_name": self.field.name if self.field else None,
            "timestamp": self.timestamp.isoformat(),
            "timestamp_local": utc_naive_to_local_iso(self.timestamp, tz_name),
            "decision": self.decision,
            "average_vwc": self.average_vwc,
            "min_vwc": self.min_vwc,
            "max_vwc": self.max_vwc,
            "num_ports_reporting": self.num_ports_reporting,
            "num_ports_below_threshold": self.num_ports_below_threshold,
            "num_ports_error": self.num_ports_error,
            "trigger_threshold": self.trigger_threshold,
            "target_vwc": self.target_vwc,
            "soil_volume_m3": self.soil_volume_m3,
            "system_flow_lps": self.system_flow_lps,
            "vwc_deficit": self.vwc_deficit,
            "liters_needed": self.liters_needed,
            "runtime_hours": self.runtime_hours,
            "runtime_minutes": self.runtime_minutes,
            "battery_percent": self.battery_percent,
            "ports": raw_ports,
        }
