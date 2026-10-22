"""Parseo de las URLs de conexión (base de datos administrada y Redis).

Las plataformas administradas (Northflank, Railway, Fly...) entregan la base y
el cache como **una sola URL**. El parseo es propio y usa solo la biblioteca
estándar: no hace falta ninguna dependencia nueva.

Formatos soportados:

- base: `postgresql://usuario:clave@host:puerto/base?sslmode=require` (también
  `postgres://`); la clave viene percent-encoded cuando tiene `@`, `:` o `/`;
- Redis: `redis://...` o `rediss://...` (TLS), con puerto y base por defecto.
"""

from urllib.parse import parse_qsl, unquote, urlsplit

POSTGRES_SCHEMES = ('postgres', 'postgresql', 'psql')
DEFAULT_POSTGRES_PORT = 5432
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DATABASE = 0


def parse_database_url(url: str, sslmode: str | None = None) -> dict:
    """Traduce una URL de base de datos a la configuración de Django.

    Args:
        url: URL de PostgreSQL, por ejemplo
            `postgresql://usuario:clave@host:5432/presto?sslmode=require`.
        sslmode: modo de SSL que pisa el de la URL (`require`, `verify-full`...).
            Si es `None`, se usa el que venga en la URL.

    Returns:
        El diccionario de conexión de Django.

    Raises:
        ValueError: si la URL no es de PostgreSQL o no tiene base de datos.
    """
    parts = urlsplit(url)
    if parts.scheme not in POSTGRES_SCHEMES:
        raise ValueError(
            f'La URL de la base tiene que ser postgresql:// (se recibió {parts.scheme!r}).'
        )

    name = unquote(parts.path.lstrip('/'))
    if not name:
        raise ValueError('La URL de la base no tiene el nombre de la base de datos.')

    options = dict(parse_qsl(parts.query))
    if sslmode:
        options['sslmode'] = sslmode

    config = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': name,
        'USER': unquote(parts.username or ''),
        'PASSWORD': unquote(parts.password or ''),
        'HOST': parts.hostname or '',
        'PORT': parts.port or DEFAULT_POSTGRES_PORT,
    }
    if options:
        config['OPTIONS'] = options
    return config


def parse_redis_url(url: str) -> str:
    """Normaliza una URL de Redis para el broker de Celery.

    Completa el puerto (`6379`) y la base (`0`) cuando no vienen, y deja el
    resto igual: el esquema (`rediss://` para TLS), las credenciales y el
    camino.

    Args:
        url: URL de Redis, por ejemplo `redis://cache.example.com`.

    Returns:
        La URL normalizada.

    Raises:
        ValueError: si la URL no es de Redis.
    """
    parts = urlsplit(url)
    if parts.scheme not in ('redis', 'rediss', 'unix'):
        raise ValueError(
            f'La URL de Redis tiene que ser redis:// o rediss:// (se recibió {parts.scheme!r}).'
        )
    if parts.scheme == 'unix':
        return url
    if not parts.hostname:
        raise ValueError('La URL de Redis no tiene host.')

    netloc = parts.hostname
    if parts.port:
        netloc = f'{netloc}:{parts.port}'
    else:
        netloc = f'{netloc}:{DEFAULT_REDIS_PORT}'
    if parts.username:
        credentials = parts.username
        if parts.password:
            credentials = f'{credentials}:{parts.password}'
        netloc = f'{credentials}@{netloc}'

    path = parts.path or f'/{DEFAULT_REDIS_DATABASE}'
    return f'{parts.scheme}://{netloc}{path}'
