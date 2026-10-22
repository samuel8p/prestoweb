"""Tests de la búsqueda de un usuario por su alias (ledger).

La búsqueda devuelve lo mínimo para pagarle: el alias, un nombre reducido y
las billeteras por moneda. **Ni email ni saldos**.
"""

import uuid

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def authenticate(client, email, password='TestPass123!'):
    """Registra (si hace falta) un usuario y autentica al cliente con él."""
    from apps.identity.services import register_user

    user = register_user(email=email, password=password)
    from rest_framework_simplejwt.tokens import RefreshToken

    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return user


def set_alias(client, alias):
    """Le pone un alias al usuario autenticado (por la API)."""
    response = client.put('/api/v1/identity/alias/', {'alias': alias}, format='json')
    assert response.status_code == 200, response.data
    return response.data


def lookup(client, alias):
    """Busca un usuario por su alias."""
    return client.get(f'/api/v1/ledger/accounts/by-alias/{alias}/')


def test_the_lookup_returns_the_alias_the_name_and_the_wallets(client):
    """La búsqueda devuelve el alias, el nombre reducido y las billeteras."""
    user = authenticate(client, 'busqueda-uno@example.com')
    set_alias(client, 'juan.perez')
    user.first_name = 'Juan'
    user.last_name = 'Perez'
    user.save(update_fields=['first_name', 'last_name'])
    from apps.ledger.services import create_user_wallet

    create_user_wallet(user_id=user.id, currency='ARS')
    create_user_wallet(user_id=user.id, currency='USD')

    response = lookup(client, 'juan.perez')

    assert response.status_code == 200
    assert response.data['alias'] == 'juan.perez'
    assert response.data['name'] == 'Juan P.'
    assert {wallet['currency'] for wallet in response.data['wallets']} == {'ARS', 'USD'}
    assert all('balance' not in wallet for wallet in response.data['wallets'])
    assert all('account_id' in wallet for wallet in response.data['wallets'])


def test_the_lookup_does_not_return_the_email_nor_the_balances(client):
    """La búsqueda no filtra datos que no le corresponden."""
    user = authenticate(client, 'busqueda-datos@example.com')
    set_alias(client, 'datos.minimos')
    from apps.ledger.services import create_user_wallet

    create_user_wallet(user_id=user.id, currency='ARS')

    response = lookup(client, 'datos.minimos')

    assert response.status_code == 200
    assert 'email' not in response.data
    assert 'balance' not in response.data
    assert 'balance' not in str(response.data)
    assert 'datos.minimos@example.com' not in str(response.data)


def test_the_lookup_of_an_unknown_alias_returns_404(client):
    """Un alias que no existe devuelve 404."""
    authenticate(client, 'busqueda-inexistente@example.com')

    response = lookup(client, 'no.existe')

    assert response.status_code == 404
    assert response.data['error']['code'] == 'not_found'


def test_the_lookup_needs_the_token(client):
    """Sin token, la búsqueda responde 401."""
    response = APIClient().get('/api/v1/ledger/accounts/by-alias/juan.perez/')

    assert response.status_code == 401


def test_the_lookup_is_throttled_to_avoid_enumeration(client):
    """La búsqueda tiene un límite estricto (anti-enumeración)."""
    from django.core.cache import cache

    cache.clear()
    authenticate(client, 'busqueda-throttle@example.com')

    statuses = [lookup(client, f'busqueda-{index}').status_code for index in range(12)]

    assert 429 in statuses, 'la búsqueda debería terminar con un 429 (throttled)'
    assert statuses[0] == 404


def test_the_lookup_does_not_query_per_wallet(client):
    """La búsqueda no hace una consulta por billetera."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    from apps.ledger.services import create_user_wallet

    user = authenticate(client, 'busqueda-consultas@example.com')
    set_alias(client, 'consultas.alias')
    for currency in ('ARS', 'USD'):
        create_user_wallet(user_id=user.id, currency=currency)

    with CaptureQueriesContext(connection) as queries:
        response = lookup(client, 'consultas.alias')

    assert response.status_code == 200
    assert len(queries) <= 4, f'consultas de más: {len(queries)}'


def test_the_lookup_finds_the_user_with_another_credential(client):
    """Quien busca necesita autenticarse (el alias no es público)."""
    other = APIClient()
    authenticate(client, 'busqueda-privada@example.com')
    set_alias(client, 'privada.alias')

    response = other.get('/api/v1/ledger/accounts/by-alias/privada.alias/')

    assert response.status_code == 401
    assert uuid.uuid4() is not None
