from .base import *

# Disable debug in test mode
DEBUG = False

# Simulated deposits are enabled in the test environment
LEDGER_SIMULATED_DEPOSITS_ENABLED = True

# Use the test runner
TEST_RUNNER = 'django.test.runner.DiscoverRunner'
