"""Tests del endpoint público de metadata y de la cabecera de modo demo."""

import pytest
from django.test import Client, override_settings

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return Client()


def test_meta_is_public_and_reports_the_production_mode(client):
    """El endpoint no pide token y dice en qué modo corre la aplicación."""
    with override_settings(DEMO_MODE=False, LEDGER_SIMULATED_DEPOSITS_ENABLED=False):
        response = client.get('/api/v1/meta/')

    assert response.status_code == 200
    assert response.json() == {'mode': 'production', 'simulated_money': False}


def test_meta_reports_the_demo_mode(client):
    """Con el modo demo activo dice que es demo y que el dinero es simulado."""
    with override_settings(DEMO_MODE=True, LEDGER_SIMULATED_DEPOSITS_ENABLED=True):
        response = client.get('/api/v1/meta/')

    assert response.status_code == 200
    assert response.json() == {'mode': 'demo', 'simulated_money': True}


def test_meta_does_not_ask_for_a_token(client):
    """Sin token el endpoint responde igual."""
    response = client.get('/api/v1/meta/')

    assert response.status_code == 200
    assert response['Content-Type'].startswith('application/json')


def test_responses_carry_the_demo_header_in_demo_mode(client):
    """En modo demo todas las respuestas llevan la cabecera X-Presto-Mode."""
    with override_settings(DEMO_MODE=True):
        response = client.get('/api/v1/meta/')
        health = client.get('/health/')

    assert response['X-Presto-Mode'] == 'demo'
    assert health['X-Presto-Mode'] == 'demo'


def test_responses_do_not_carry_the_demo_header_outside_demo_mode(client):
    """Fuera del modo demo la cabecera no aparece."""
    response = client.get('/api/v1/meta/')
    health = client.get('/health/')

    assert 'X-Presto-Mode' not in response
    assert 'X-Presto-Mode' not in health
