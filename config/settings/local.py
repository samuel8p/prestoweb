from .base import *

# Development overrides
DEBUG = True


# Use console backend for emails in development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
