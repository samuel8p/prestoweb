from .base import *

# Disable debug in test mode
DEBUG = False

# Simulated deposits are enabled in the test environment
LEDGER_SIMULATED_DEPOSITS_ENABLED = True

# The demo mode is off in the tests: they enable it explicitly when they need it
DEMO_MODE = False

# Use the test runner
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Celery: las tareas corren en el proceso, sin broker (los tests no dependen de Redis)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'

# Email: backend en memoria, los tests no mandan nada real
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
