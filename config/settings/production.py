from .base import *

# Production overrides
DEBUG = False

# Security: enforce HTTPS settings (will be set by reverse proxy)
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
