from .base import *

# Test settings – use a dedicated PostgreSQL database
DATABASES["default"]["NAME"] = os.getenv("TEST_DATABASE_NAME", "presto_test")

# Disable debug in test mode
DEBUG = False

# Use the test runner
TEST_RUNNER = "django.test.runner.DiscoverRunner"