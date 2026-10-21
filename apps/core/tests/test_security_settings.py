"""Tests de la política de contraseñas y de la seguridad de producción."""

import os
import subprocess
import sys

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def read_setting(setting: str, **environment: str) -> str:
    """Lee un setting de los settings de producción en un subproceso.

    Args:
        setting: nombre del setting.
        environment: variables de entorno para el subproceso.

    Returns:
        El valor del setting.
    """
    env = {key: value for key, value in os.environ.items() if not key.startswith('EMAIL_')}
    env.update(environment)
    env['DJANGO_SETTINGS_MODULE'] = 'config.settings.production'
    env.setdefault('DJANGO_SECRET_KEY', 'clave-de-prueba-para-el-check-de-produccion-1234567890')
    env.setdefault('DJANGO_ALLOWED_HOSTS', 'presto.example.com')
    result = subprocess.run(
        [
            sys.executable,
            '-c',
            f'from django.conf import settings; print(getattr(settings, "{setting}"))',
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_register_rejects_a_numeric_password(client):
    """Una contraseña solo numérica devuelve 400 (validador de Django)."""
    response = client.post(
        '/api/v1/auth/register/',
        {'email': 'numerico@example.com', 'password': '1234567890'},
        format='json',
    )

    assert response.status_code == 400
    assert response.data['error']['code'] == 'validation_error'


def test_register_rejects_a_common_password(client):
    """Una contraseña común devuelve 400 (validador de Django)."""
    response = client.post(
        '/api/v1/auth/register/',
        {'email': 'comun@example.com', 'password': 'password123'},
        format='json',
    )

    assert response.status_code == 400


def test_the_password_validators_are_enabled():
    """Los validadores de contraseña de Django están activos (AGENTS §9.5)."""
    from django.conf import settings

    validators = {validator['NAME'] for validator in settings.AUTH_PASSWORD_VALIDATORS}

    assert 'django.contrib.auth.password_validation.MinimumLengthValidator' in validators
    assert 'django.contrib.auth.password_validation.CommonPasswordValidator' in validators
    assert 'django.contrib.auth.password_validation.NumericPasswordValidator' in validators
    assert 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator' in validators


def test_production_enables_hsts():
    """En producción el HSTS está activado (AGENTS §9.4)."""
    seconds = int(read_setting('SECURE_HSTS_SECONDS'))

    assert seconds > 0
    assert read_setting('SECURE_HSTS_INCLUDE_SUBDOMAINS') == 'True'


def test_the_production_settings_pass_the_deploy_check():
    """Los settings de producción pasan el `check --deploy` sin avisos.

    La CI corre este mismo chequeo con `--fail-level WARNING`: cualquier
    aviso de seguridad nuevo rompe la build.
    """
    env = {key: value for key, value in os.environ.items() if not key.startswith('EMAIL_')}
    env.update(
        {
            'DJANGO_SETTINGS_MODULE': 'config.settings.production',
            'DJANGO_SECRET_KEY': 'clave-de-prueba-para-el-check-de-produccion-1234567890abcdefghij',
            'DJANGO_ALLOWED_HOSTS': 'presto.example.com',
            'DJANGO_DEBUG': '0',
            'REDIS_URL': 'redis://localhost:6379/0',
        }
    )
    result = subprocess.run(
        [sys.executable, 'manage.py', 'check', '--deploy', '--fail-level', 'WARNING'],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
