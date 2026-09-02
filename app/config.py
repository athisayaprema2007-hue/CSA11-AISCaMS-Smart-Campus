"""Application configuration objects."""

import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")


class BaseConfig:
    """Default configuration shared by every environment."""

    SECRET_KEY = os.environ.get("AISCAMS_SECRET_KEY", "aiscams-local-development-key")
    DATABASE_PATH = os.environ.get("AISCAMS_DB", os.path.join(INSTANCE_DIR, "aiscams.db"))
    SEED_ON_STARTUP = True
    JSON_SORT_KEYS = False
    TEMPLATES_AUTO_RELOAD = True

    # Demo passwords are intentionally simple: the system runs fully offline.
    DEMO_PASSWORD = "campus123"


class TestConfig(BaseConfig):
    """Configuration used by the Pytest suite (isolated temporary database)."""

    TESTING = True
    SEED_ON_STARTUP = False
    WTF_CSRF_ENABLED = False


CONFIGS = {"default": BaseConfig, "testing": TestConfig}
