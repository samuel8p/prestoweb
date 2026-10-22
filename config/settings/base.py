import logging
import os
from datetime import timedelta
from pathlib import Path

from apps.core.connections import parse_database_url, parse_redis_url

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
    DATABASES['default'] = parse_database_url(
        db_url,
        sslmode=os.getenv('DB_SSLMODE') or None,
    )
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
        # El mismo `type` del ledger aparece en el detalle y en el listado.
        'LedgerTransactionTypeEnum': 'apps.ledger.models.LedgerTransaction.Type',
    },
    # Los hooks: el de drf-spectacular (los enums) y los dos del proyecto (la
    # respuesta CSV de los reportes y los errores de cada operación). La lista
    # **reemplaza** la de drf-spectacular, así que hay que volver a poner la
    # de por defecto.
    'POSTPROCESSING_HOOKS': [
        'drf_spectacular.hooks.postprocess_schema_enums',
        'apps.core.hooks.add_csv_response_to_the_reports',
        'apps.core.hooks.add_error_responses',
        'apps.core.hooks.add_nullable_responses',
        'apps.core.hooks.add_demo_mode_header',
    ],
}

MIDDLEWARE = [
    # El CORS va lo más arriba posible: tiene que responder los preflight
    # OPTIONS antes de que otro middleware genere la respuesta.
    'corsheaders.middleware.CorsMiddleware',
    'apps.core.middleware.DemoModeHeaderMiddleware',
    # El chequeo de salud se contesta antes de que Django valide el `Host`:
    # las plataformas lo llaman con la IP interna del servicio.
    'apps.core.middleware.HealthCheckMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # whitenoise sirve los archivos estáticos (el admin) desde la propia
    # aplicación: sin un servidor de estáticos aparte, el admin salía sin
    # estilos.
    'whitenoise.middleware.WhiteNoiseMiddleware',
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

# Password validators (AGENTS §9.5: los validadores de Django, activos)
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

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

# Redis: broker de Celery (el servicio redis ya existe en docker-compose.yml).
# La URL se normaliza (puerto y base por defecto) para que la que dan las
# plataformas administradas sirva tal cual.
REDIS_URL = parse_redis_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

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

# CORS (AGENTS §9.3): el front vive en otro origen (Vercel), así que la API
# responde con los headers de CORS.
# - Los orígenes vienen de `CORS_ALLOWED_ORIGINS`, separados por comas.
# - Nunca se usa `*`: una lista vacía significa "ningún origen permitido".
# - No se permiten credenciales: la autenticación va en `Authorization: Bearer`.
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if origin.strip()
]
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = False
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
CORS_EXPOSE_HEADERS = ['Content-Type']

# Static files (CSS, JavaScript, Images)
# Los sirve la propia aplicación con whitenoise (no hay nginx delante): sin
# esto, el admin del Django salía sin estilos en producción.
STATIC_URL = '/static/'
STATIC_ROOT = str(BASE_DIR / 'staticfiles')
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        # Comprimidos y sin manifiesto: el manifiesto exige que los estáticos
        # estén recolectados, y sin ellos (desarrollo, tests) rompe las
        # páginas del admin. La imagen de producción sí los recolecta.
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}
WHITENOISE_MAX_AGE = 3600
WHITENOISE_AUTOREFRESH = True
# En desarrollo los estáticos no están recolectados: whitenoise los busca en
# las apps (igual que hacía el runserver).
WHITENOISE_USE_FINDERS = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'identity.User'

# Logging
logger = logging.getLogger(__name__)
