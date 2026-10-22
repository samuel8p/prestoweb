"""Tests del endpoint de estado de salud (`/health/`)."""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from django.db import OperationalError
from django.test import Client, override_settings

pytestmark = pytest.mark.django_db

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def client():
    return Client()


def test_health_check_returns_ok_when_the_database_answers(client):
    """Con la base respondiendo el chequeo devuelve 200 y el estado ok."""
    response = client.get('/health/')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_health_check_does_not_require_authentication(client):
    """El chequeo de salud es público: no pide credenciales."""
    response = client.get('/health/')

    assert response.status_code == 200


def test_health_check_returns_503_when_the_database_fails(client):
    """Si la base no responde el chequeo devuelve 503."""
    with patch('django.db.connection.cursor', side_effect=OperationalError('sin base')):
        response = client.get('/health/')

    assert response.status_code == 503


def test_health_check_does_not_leak_internal_details(client):
    """El cuerpo del error no revela detalles internos de la base."""
    with patch('django.db.connection.cursor', side_effect=OperationalError('sin base')):
        response = client.get('/health/')

    body = response.json()
    assert body == {'status': 'unavailable'}
    assert 'sin base' not in response.content.decode()


def test_the_production_healthcheck_sends_an_allowed_host():
    """El health check de producción manda un Host permitido.

    Django responde 400 cuando el header `Host` no está en `ALLOWED_HOSTS`, y
    el chequeo interno del contenedor usa `127.0.0.1`: sin ese header el
    contenedor de producción queda siempre `unhealthy`.
    """
    compose = yaml.safe_load((ROOT / 'docker-compose.prod.yml').read_text(encoding='utf-8'))
    command = ' '.join(compose['services']['web']['healthcheck']['test'])

    assert 'Host' in command
    assert 'ALLOWED_HOSTS' in command


def test_the_health_check_answers_with_a_host_that_is_not_allowed(client):
    """El chequeo de salud responde igual si el `Host` no está en `ALLOWED_HOSTS`.

    Las plataformas mandan el chequeo a la IP interna del servicio: Django
    respondería 400 y el servicio quedaría marcado como unhealthy. El
    endpoint es público y no dice nada del servicio más que "la base
    contesta", así que se contesta antes de la validación del `Host`.
    """
    with override_settings(ALLOWED_HOSTS=['presto.example.com']):
        response = client.get('/health/', HTTP_HOST='10.42.0.7:8000')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_the_other_endpoints_still_reject_an_unknown_host(client):
    """El resto de los endpoints siguen validando el `Host`."""
    with override_settings(ALLOWED_HOSTS=['presto.example.com']):
        response = client.get('/api/v1/meta/', HTTP_HOST='10.42.0.7:8000')

    assert response.status_code == 400


def test_the_allowed_hosts_come_from_the_environment():
    """`DJANGO_ALLOWED_HOSTS` define los hosts, separados por comas."""
    import os
    import subprocess
    import sys

    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ('DJANGO_ALLOWED_HOSTS', 'DJANGO_SETTINGS_MODULE')
    }
    env['DJANGO_SETTINGS_MODULE'] = 'config.settings.base'
    env['DJANGO_ALLOWED_HOSTS'] = 'presto.example.com,presto-front.vercel.app'

    result = subprocess.run(
        [sys.executable, '-c', 'from django.conf import settings; print(settings.ALLOWED_HOSTS)'],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert 'presto.example.com' in result.stdout
    assert 'presto-front.vercel.app' in result.stdout
    assert '*' not in result.stdout
