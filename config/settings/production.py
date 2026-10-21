import os

from django.core.exceptions import ImproperlyConfigured

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

# Celery: el broker es obligatorio en producción, no hay default silencioso
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or os.environ.get('REDIS_URL')
if not CELERY_BROKER_URL:
    raise ImproperlyConfigured(
        'CELERY_BROKER_URL o REDIS_URL son obligatorios en producción para levantar el worker.'
    )
