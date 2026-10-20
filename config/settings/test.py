from .base import *

# Test settings – use the existing PostgreSQL database
# (the production DB already has auth tables via migrations)
DATABASES["default"] = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": "presto",
    "USER": os.getenv("POSTGRES_USER", "presto"),
    "PASSWORD": os.getenv("POSTGRES_PASSWORD", "presto"),
    "HOST": os.getenv("POSTGRES_HOST", "localhost"),
    "PORT": os.getenv("POSTGRES_PORT", "5432"),
    # Reuse existing test database instead of creating a new one
    "TEST": {
        "KEEPDB": True,
    },
}

# Disable debug in test mode
DEBUG = False

# Use the test runner
TEST_RUNNER = "django.test.runner.DiscoverRunner"