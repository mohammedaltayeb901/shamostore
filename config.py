import os

from dotenv import load_dotenv

BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, ".env"))


def _database_uri():
    """Prefer DATABASE_URL, normalising the legacy postgres:// scheme."""
    uri = os.environ.get("DATABASE_URL")
    if not uri:
        return "sqlite:///" + os.path.join(BASEDIR, "instance", "shamostore.db")
    if uri.startswith("postgres://"):
        uri = "postgresql+psycopg://" + uri[len("postgres://"):]
    elif uri.startswith("postgresql://"):
        uri = "postgresql+psycopg://" + uri[len("postgresql://"):]
    return uri


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"

    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    STORE_NAME = os.environ.get("STORE_NAME") or "شامو ستور"
    CURRENCY_SYMBOL = os.environ.get("CURRENCY_SYMBOL") or "$"

    MIN_TOPUP = 1
    MAX_TOPUP = 5000

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME") or "admin"
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL") or "admin@shamostore.com"
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD") or "Admin@12345"

    # الحساب التجريبي يُنشأ فقط بأمر "flask seed-demo" ويمكن تعطيله من البيئة.
    ENABLE_DEMO_ACCOUNT = os.environ.get("ENABLE_DEMO_ACCOUNT", "true").lower() != "false"

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    WTF_CSRF_TIME_LIMIT = None


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SERVER_NAME = "localhost"
