import logging
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/releases/5.0/#new-settings

# SECURITY WARNING: keep the secret key secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-dev-key-do-not-use-in-prod')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', '1') == '1'

ALLOWED_HOSTS = (
    os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',') if os.getenv('DJANGO_ALLOWED_HOSTS') else []
)

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {}
db_url = os.getenv('DATABASE_URL')
if db_url:
    import dj_database_url

    DATABASES['default'] = dj_database_url.parse(db_url)
else:
    # Fallback to PostgreSQL using environment variables
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'presto'),
        'USER': os.getenv('POSTGRES_USER', 'presto'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'presto'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }

# Application definition
INSTALLED_APPS = [
    # Django core apps
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Core apps
    'apps.core',
    'apps.identity',
    'apps.ledger',
    'apps.offers',
    'apps.loans',
    'apps.investments',
    'apps.budgets',
    'apps.reports',
    'apps.notifications',
    # Third party
    'rest_framework',
    'drf_spectacular',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
]

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.StandardPagination',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'apps.core.exception_handler.api_exception_handler',
    'DEFAULT_THROTTLE_RATES': {
        'login': '5/min',
        'register': '5/hour',
    },
}

# JWT (simplejwt)
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# drf-spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'Presto API',
    'DESCRIPTION': 'API de finanzas e inversiones con marketplace de préstamos.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/v1',
    # Nombres explícitos para los choice sets de `status` que colisionaban entre
    # componentes (el de los préstamos y el de las posiciones de inversión).
    'ENUM_NAME_OVERRIDES': {
        'LoanStatusEnum': 'apps.loans.models.Loan.Status',
        'PositionStatusEnum': 'apps.investments.models.Position.Status',
    },
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'apps.core.middleware.DemoModeHeaderMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

ASGI_APPLICATION = 'config.asgi.application'

ROOT_URLCONF = 'config.urls'

# Password validators
AUTH_PASSWORD_VALIDATORS = []

# Password hashers: Argon2 first, then Django built-in hashers
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Environment marker used by the system checks (never rely on DEBUG)
DJANGO_ENV = os.getenv('DJANGO_ENV', 'local')

# Redis: broker de Celery (el servicio redis ya existe en docker-compose.yml)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Email: las notificaciones se envían por email. En desarrollo el backend es
# de consola; en producción, SMTP configurado por variables de entorno.
# Email: en modo demo (sin EMAIL_HOST) los avisos de las notificaciones salen
# por consola, o sea en los logs del worker. Si EMAIL_HOST está definido, el
# backend por defecto pasa a ser SMTP. Un EMAIL_BACKEND explícito manda siempre.
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    (
        'django.core.mail.backends.smtp.EmailBackend'
        if EMAIL_HOST
        else 'django.core.mail.backends.console.EmailBackend'
    ),
)
EMAIL_PORT = int(os.getenv('EMAIL_PORT') or 587)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').strip().lower() == 'true'
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'no-reply@presto.local')

# Celery (AGENTS §3 y §4): tareas asíncronas y periódicas con Redis como broker.
# No hay result backend persistente: las tareas del proyecto no devuelven
# resultados, solo efectos sobre el ledger.
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = None
CELERY_TASK_IGNORE_RESULT = True
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 15 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 10 * 60
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_WORKER_HIJACK_ROOT_LOGGER = False

# Demo mode: with DEMO_MODE=true the stack behaves like a demo (the simulated
# deposits are enabled and the ledger system check allows them). Without it,
# the simulated deposits are only for local/test environments.
DEMO_MODE = os.getenv('DEMO_MODE', 'False').strip().lower() == 'true'

# Ledger: simulated deposits are only for local/test environments
LEDGER_SIMULATED_DEPOSITS_ENABLED = DEMO_MODE or (
    os.getenv('LEDGER_SIMULATED_DEPOSITS_ENABLED', 'False').strip().lower() == 'true'
)

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = str(BASE_DIR / 'staticfiles')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'identity.User'

# Logging
logger = logging.getLogger(__name__)
