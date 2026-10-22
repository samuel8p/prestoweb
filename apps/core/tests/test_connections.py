"""Tests del parseo de las URLs de conexión (base administrada y Redis)."""

import os
import subprocess
import sys

import pytest

from apps.core.connections import parse_database_url, parse_redis_url


def test_a_plain_database_url_is_parsed():
    """Una URL `postgresql://usuario:clave@host:puerto/base` se traduce a la config de Django."""
    config = parse_database_url('postgresql://usuario:clave@db.example.com:5432/presto')

    assert config['ENGINE'] == 'django.db.backends.postgresql'
    assert config['NAME'] == 'presto'
    assert config['USER'] == 'usuario'
    assert config['PASSWORD'] == 'clave'
    assert config['HOST'] == 'db.example.com'
    assert config['PORT'] == 5432


def test_the_password_with_special_characters_is_unquoted():
    """Una clave con `@`, `:` y `/` viene percent-encoded en la URL."""
    config = parse_database_url(
        'postgresql://usuario:p%40ss%3Aw%2Frd%20con%20espacios@db.example.com:5432/presto'
    )

    assert config['PASSWORD'] == 'p@ss:w/rd con espacios'
    assert config['USER'] == 'usuario'


def test_the_postgres_scheme_is_accepted():
    """`postgres://` (el esquema corto) también sirve."""
    config = parse_database_url('postgres://usuario:clave@db.example.com:5432/presto')

    assert config['ENGINE'] == 'django.db.backends.postgresql'
    assert config['HOST'] == 'db.example.com'


def test_the_sslmode_of_the_url_is_kept():
    """El `sslmode` que viene en la URL se respeta."""
    config = parse_database_url(
        'postgresql://usuario:clave@db.example.com:5432/presto?sslmode=require'
    )

    assert config['OPTIONS'] == {'sslmode': 'require'}


def test_the_sslmode_of_the_environment_wins():
    """`DB_SSLMODE` pisa el `sslmode` de la URL (la base administrada lo exige)."""
    config = parse_database_url(
        'postgresql://usuario:clave@db.example.com:5432/presto?sslmode=prefer',
        sslmode='require',
    )

    assert config['OPTIONS'] == {'sslmode': 'require'}


def test_without_sslmode_there_are_no_options():
    """Sin `sslmode` no se agregan opciones: es el comportamiento de siempre."""
    config = parse_database_url('postgresql://usuario:clave@db.example.com:5432/presto')

    assert 'OPTIONS' not in config


def test_a_url_without_password_is_parsed():
    """Una URL sin clave (o con la clave vacía) se acepta."""
    config = parse_database_url('postgresql://usuario@db.example.com:5432/presto')

    assert config['USER'] == 'usuario'
    assert config['PASSWORD'] == ''


def test_a_url_without_port_uses_the_postgres_one():
    """Sin puerto explícito se usa el 5432 de PostgreSQL."""
    config = parse_database_url('postgresql://usuario:clave@db.example.com/presto')

    assert config['PORT'] == 5432


def test_an_unsupported_scheme_is_rejected():
    """Una URL que no es de PostgreSQL se rechaza con un error claro."""
    with pytest.raises(ValueError, match='postgresql'):
        parse_database_url('mysql://usuario:clave@db.example.com:3306/presto')


def test_the_redis_url_gets_the_default_port_and_database():
    """Una URL de Redis sin puerto ni base se normaliza."""
    assert parse_redis_url('redis://cache.example.com') == 'redis://cache.example.com:6379/0'


def test_the_redis_url_keeps_the_scheme_and_the_credentials():
    """`rediss://` (TLS) y las credenciales se conservan."""
    assert parse_redis_url('rediss://user:p%40ss@cache.example.com:6380/2') == (
        'rediss://user:p%40ss@cache.example.com:6380/2'
    )


def test_the_settings_use_the_database_url_when_it_is_defined():
    """Con `DATABASE_URL` la configuración de la base sale de la URL."""
    env = {
        **os.environ,
        'DJANGO_SETTINGS_MODULE': 'config.settings.base',
        'DATABASE_URL': 'postgresql://usuario:clave@db.example.com:5432/presto',
    }
    env.pop('POSTGRES_HOST', None)

    result = subprocess.run(
        [
            sys.executable,
            '-c',
            (
                'from django.conf import settings; '
                "print(settings.DATABASES['default']['HOST'], "
                "settings.DATABASES['default']['NAME'], "
                "settings.DATABASES['default']['PASSWORD'])"
            ),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.split() == ['db.example.com', 'presto', 'clave']


def test_without_the_database_url_the_individual_variables_are_used():
    """Sin `DATABASE_URL` el comportamiento de siempre: las variables sueltas."""
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        not in (
            'DATABASE_URL',
            'POSTGRES_HOST',
            'POSTGRES_DB',
            'POSTGRES_USER',
            'DJANGO_SETTINGS_MODULE',
        )
    }
    env['DJANGO_SETTINGS_MODULE'] = 'config.settings.base'
    env['POSTGRES_HOST'] = 'postgres.interno'
    env['POSTGRES_DB'] = 'presto'

    result = subprocess.run(
        [
            sys.executable,
            '-c',
            (
                'from django.conf import settings; '
                "print(settings.DATABASES['default']['HOST'], "
                "settings.DATABASES['default']['NAME'])"
            ),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.split() == ['postgres.interno', 'presto']


def test_the_celery_broker_comes_from_the_redis_url():
    """El broker de Celery sale de `REDIS_URL` cuando no se define aparte."""
    env = {
        **os.environ,
        'DJANGO_SETTINGS_MODULE': 'config.settings.base',
        'REDIS_URL': 'redis://cache.example.com:6379/0',
    }
    env.pop('CELERY_BROKER_URL', None)

    result = subprocess.run(
        [
            sys.executable,
            '-c',
            'from django.conf import settings; print(settings.CELERY_BROKER_URL)',
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == 'redis://cache.example.com:6379/0'
