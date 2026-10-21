import os

from .base import *

# Production overrides
DEBUG = False

# Environment marker: the system checks rely on it, never on DEBUG
DJANGO_ENV = 'production'

# Simulated deposits must stay off in production (a system check enforces it)
LEDGER_SIMULATED_DEPOSITS_ENABLED = (
    os.getenv('LEDGER_SIMULATED_DEPOSITS_ENABLED', 'False') == 'True'
)

# Security: enforce HTTPS settings (will be set by reverse proxy)
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
