"""Tests del endpoint de estado de salud (`/health/`)."""

from unittest.mock import patch

import pytest
from django.db import OperationalError
from django.test import Client

pytestmark = pytest.mark.django_db


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
