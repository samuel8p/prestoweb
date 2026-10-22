import os

from django.core.exceptions import ImproperlyConfigured

from .base import *

# Production overrides
DEBUG = False

# Environment marker: the system checks rely on it, never on DEBUG
DJANGO_ENV = 'production'

# Simulated deposits must stay off in production (a system check enforces it).
# The only exception is the demo mode, where DEMO_MODE=true enables them on
# purpose and the check lets them pass.
LEDGER_SIMULATED_DEPOSITS_ENABLED = DEMO_MODE or (
    os.getenv('LEDGER_SIMULATED_DEPOSITS_ENABLED', 'False').strip().lower() == 'true'
)

# Security: enforce HTTPS settings (will be set by reverse proxy)
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# HSTS (AGENTS §9.4). No se activa el preload: es irreversible y exige que
# todos los subdominios sirvan HTTPS.
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS') or 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# El preload del HSTS queda apagado a propósito: es irreversible y exige que
# todos los subdominios sirvan HTTPS. La decisión es del cliente, así que el
# aviso que lo pide (security.W021) se silencia con esa razón.
SILENCED_SYSTEM_CHECKS = ['security.W021']
# El proxy inverso (Nginx o Caddy) termina TLS y reenvía X-Forwarded-Proto.
# Sin esto, SECURE_SSL_REDIRECT redirigía en loop y el chequeo de salud
# (/health/) recibía un 301 en vez de un 200.
#
# Las plataformas administradas (Northflank, Railway, Fly...) también terminan
# TLS y reenvían X-Forwarded-Proto, así que el mismo ajuste sirve.
#
# Cómo comprobarlo (con el dominio público):
#   curl -i https://<dominio>/health/ | head -1
#     -> HTTP/2 200 (si el proxy no manda la cabecera, se ve un 301)
#   curl -i http://<dominio>/health/ | head -1
#     -> HTTP/2 301 (redirección a https, la que hace SECURE_SSL_REDIRECT)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Celery: el broker es obligatorio en producción, no hay default silencioso
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or os.environ.get('REDIS_URL')
if not CELERY_BROKER_URL:
    raise ImproperlyConfigured(
        'CELERY_BROKER_URL o REDIS_URL son obligatorios en producción para levantar el worker.'
    )
