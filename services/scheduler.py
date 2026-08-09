from apscheduler.schedulers.background import BackgroundScheduler


def start_scheduler(app):
    """
    Runs a check for every field once a day. This is intentionally
    simple: it doesn't yet honor each field's individual
    check_frequency_days (a per-field "last checked" comparison would
    be needed for that) — it just re-checks everything daily. Good
    enough to prove the automation runs unattended; refine later if
    fields need genuinely different cadences.
    """
    scheduler = BackgroundScheduler()

    def job():
        with app.app_context():
            from services.checker import run_check_for_all_fields
            run_check_for_all_fields()

    scheduler.add_job(job, "interval", days=1)
    scheduler.start()
    app.extensions["scheduler"] = scheduler
