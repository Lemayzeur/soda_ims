# SoDA Irrigation Portal — Flask Server

A working Flask backend + vanilla JS/HTML/CSS frontend for the SoDA
(Sustainable & Digital Agriculture Lab) irrigation automation system.
This replaces the earlier static HTML mockup with a real, persistent,
CRUD-backed application.

## What's real vs. placeholder

- **Fields, loggers, admins, alert history, irrigation log** — fully
  real, backed by SQLite via SQLAlchemy. CRUD works end-to-end.
- **Sensor readings** — pulled from the real ZentraCloud API if you set
  `ZENTRA_TOKEN` and `DEMO_MODE=false` in `.env`. With `DEMO_MODE=true`
  (the default), the app generates plausible random VWC readings
  instead, so the whole portal is click-through-able with zero
  hardware or credentials.
- **Email alerts** — real Gmail SMTP sending, if `GMAIL_ADDRESS` and
  `GMAIL_APP_PASSWORD` are set. Without them, alerts are still
  calculated and logged, just not emailed (a warning is logged
  instead, nothing crashes).
- **Weather forecast page** — a template only, as intended. The API
  (`/api/forecast/<field_id>`) returns the correct response shape but
  with null values, so the frontend honestly shows "—" rather than
  fake numbers. Swap the body of `services/forecast_service.py` for a
  real forecast API call (Open-Meteo, NOAA NDFD, etc.) when ready —
  the frontend doesn't need to change.
- **Scheduler** — an optional daily background check via APScheduler,
  off by default (`SCHEDULER_ENABLED=false`). It currently re-checks
  every field daily rather than respecting each field's own
  `check_frequency_days`/`start_date` — a good next step if you want
  true per-field cadences (the data needed for it — `start_date` and
  `next_check_due` — is already captured and shown on the dashboard).
- **Timezones** — every field has its own IANA timezone
  (`services/tz_utils.py`, backed by `pytz`). All datetimes in the
  database are stored as naive UTC; conversion only happens at the
  edges — a form's `start_date` is interpreted as local wall-clock
  time in that field's zone and converted to UTC on save, and every
  API response includes both the raw UTC value and a `_local`
  version for display. Verified against known UTC offsets (e.g. 6:00
  AM Central in August → 11:00 UTC, correctly reflecting CDT) before
  wiring it through the rest of the app.
- **Per-sensor detail on the dashboard** — each field row has a
  "▸ Sensors" toggle, closed by default, that expands to show every
  logger's individual port readings with a below-threshold flag,
  without needing a page reload (the data was already being captured
  per check, just not surfaced in the UI before).
- **Rate limiting** — `services/rate_limiter.py` paces live ZentraCloud
  calls to stay under their documented limits (60 calls/minute per
  account, 1 call/minute per device — see their US Server API docs).
  It's in-memory and per-process, which is fine for a single Flask
  worker; it won't coordinate across multiple worker processes.

## Setup

```bash
cd soda_server
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then edit .env with real values
python3 app.py
```

Visit http://127.0.0.1:5000 — the database is created and seeded
automatically on first run (SQLite file `soda.db`), pre-populated with
the six example fields (Vineyard, Organic Farm, Lee Farm, Blueberry
Farm, South Farm, Bradford Farm) and the three admin emails, so
there's something to look at immediately.

## Project structure

```
soda_server/
  app.py                    # Flask app factory + entry point
  config.py                 # env-driven configuration
  models.py                 # SQLAlchemy models: Field, Logger, AdminEmail,
                             #   AlertLog, IrrigationLog
  seed.py                   # first-run demo data
  routes/                   # one blueprint per resource
    fields.py                #   Field CRUD + nested logger creation
    loggers.py                #   Logger update/delete
    admins.py                  #   Admin email CRUD
    dashboard.py                #   aggregated dashboard summary
    checks.py                    #   POST /api/check-now (all or one field)
    alerts.py                     #   alert history
    forecast.py                    #   forecast template
    export.py                       #   CSV downloads
  services/                 # the actual business logic
    zentra_client.py          #   ZentraCloud API calls + demo fallback
    calculations.py             #   threshold/deficit/runtime math
    email_service.py              #   Gmail SMTP sending
    csv_export.py                   #   CSV generation
    checker.py                       #   orchestrates the above for one check
    forecast_service.py                # placeholder forecast data
    scheduler.py                        # optional daily background job
  static/
    css/style.css
    js/{api,app,dashboard,fields,alerts,forecast}.js
  templates/
    index.html               # single shell, 4 pages, JS-driven
```

## API reference (quick)

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/api/fields` | list / create fields |
| GET/PUT/DELETE | `/api/fields/<id>` | one field |
| POST | `/api/fields/<id>/loggers` | add a logger to a field |
| PUT/DELETE | `/api/loggers/<id>` | edit / remove a logger |
| GET/POST | `/api/admins` | list / add admin emails |
| DELETE | `/api/admins/<id>` | remove an admin |
| GET | `/api/dashboard` | latest status per field + summary counts |
| POST | `/api/check-now` | run a check for every field right now |
| POST | `/api/check-now/<field_id>` | run a check for one field |
| GET | `/api/alerts` | alert history |
| GET | `/api/forecast/<field_id>` | forecast template |
| GET | `/api/export/{irrigation-log,fields,alerts}` | CSV downloads |

## Tested

All CRUD endpoints, validation (duplicate names return 409), the full
check-now pipeline (fetch → calculate → log → email-or-skip), forecast
template, and CSV export were exercised directly against a running
instance before this was handed off — not just read over.

## Known limitations / next steps

- The dev server (`app.run()`) is for local testing only — deploy
  behind gunicorn/uWSGI + nginx for anything real.
- No authentication yet. Anyone who can reach the server can edit
  fields, admins, and trigger irrigation checks. Worth adding before
  this leaves your lab network.
- The scheduler doesn't yet honor per-field `check_frequency_days`
  individually — it re-checks everything daily.
- Editing a field is now wired up end-to-end (pulls current data,
  populates the form including loggers, saves via PUT — loggers are
  replaced wholesale rather than diffed, which is simpler and
  predictable but means logger IDs change on every edit).
- On your ZentraCloud paid account: their docs describe the rate limit
  at the "user"/account level (60 calls/minute), not explicitly per
  token — so a second token on the same account likely shares the
  same quota rather than doubling it. Worth confirming directly with
  Zentra support if this matters for your setup, since their docs
  don't explicitly address the multi-token-same-account case.
