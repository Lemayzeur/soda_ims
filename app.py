from flask import Flask, render_template

from config import Config
from models import db
from seed import seed_if_empty

from routes.fields import fields_bp
from routes.loggers import loggers_bp
from routes.admins import admins_bp
from routes.dashboard import dashboard_bp
from routes.checks import checks_bp
from routes.alerts import alerts_bp
from routes.forecast import forecast_bp
from routes.export import export_bp
from routes.meta import meta_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    app.register_blueprint(fields_bp)
    app.register_blueprint(loggers_bp)
    app.register_blueprint(admins_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(checks_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(forecast_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(meta_bp)

    with app.app_context():
        db.create_all()
        seed_if_empty()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(404)
    def not_found(e):
        return {"error": "not found"}, 404

    @app.errorhandler(500)
    def server_error(e):
        return {"error": "internal server error"}, 500

    if app.config.get("SCHEDULER_ENABLED"):
        from services.scheduler import start_scheduler
        start_scheduler(app)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
