import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'soda.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ZENTRA_TOKEN = os.getenv("ZENTRA_TOKEN", "")
    ZENTRA_BASE_URL = "https://zentracloud.com/api/v3"

    GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

    # With no Zentra token, the app generates realistic-looking demo
    # readings instead of calling the real API, so the whole portal is
    # click-through-able without live hardware or credentials.
    DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

    CHECK_FREQUENCY_DAYS = int(os.getenv("CHECK_FREQUENCY_DAYS", "5"))
    SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"
