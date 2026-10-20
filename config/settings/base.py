import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/releases/5.0/#new-settings

# SECURITY WARNING: keep the secret key secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-key-do-not-use-in-prod")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"

ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if os.getenv("DJANGO_ALLOWED_HOSTS") else []

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {}
db_url = os.getenv("DATABASE_URL")
if db_url:
    # dj_database_url parsing
    import dj_database_url
    DATABASES["default"] = dj_database_url.db_url(db_url)
else:
    # Fallback to PostgreSQL using environment variables
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "presto"),
        "USER": os.getenv("POSTGRES_USER", "presto"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "presto"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }

# Application definition
INSTALLED_APPS = [
    # Django core apps
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Core apps
    "apps.core",
    "apps.identity",

    # Third party
    "rest_framework",
    "drf_spectacular",
]

MIDDLEWARE = []

ROOT_URLCONF = "config.urls"

TEMPLATES = []

WSGI_APPLICATION = "config.wsgi.application"

ASGI_APPLICATION = "config.asgi.application"

# Password validators
AUTH_PASSWORD_VALIDATORS = []

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = str(BASE_DIR / "staticfiles")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom user model
AUTH_USER_MODEL = "identity.User"

# Logging
import logging
logger = logging.getLogger(__name__)