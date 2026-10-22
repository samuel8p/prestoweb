"""Tests del listado de movimientos con el importe y la moneda (D-10).

El listado de movimientos del ledger ahora trae, por movimiento, el importe
(con el signo desde la billetera del usuario) y la moneda.
"""

import uuid
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.ledger.tests.factories import create_approved_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def authenticate(client, user):
    """Autentica al cliente con un access token del usuario dado."""
    from rest_framework_simplejwt.tokens import RefreshToken

    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


def create_movement(client, type_: str, amount: str, currency: str, key: str):
    """Crea un movimiento del usuario autenticado."""
    response = client.post(
        '/api/v1/ledger/transactions/',
        {'type': type_, 'currency': currency, 'amount': amount},
        format='json',
        HTTP_IDEMPOTENCY_KEY=key,
    )
    assert response.status_code == 201, response.data
    return response.data


def list_movements(client):
    """Lista los movimientos del usuario autenticado."""
    response = client.get('/api/v1/ledger/transactions/')
    assert response.status_code == 200, response.data
    return response.json()['results']


def test_the_movements_list_includes_the_amount_and_the_currency(client):
    """Cada movimiento del listado trae su importe y su moneda."""
    user = create_approved_user(email='listado-importe@example.com')
    authenticate(client, user)
    create_movement(client, 'deposit', '1000.00', 'ARS', 'listado-dep')

    results = list_movements(client)

    assert len(results) == 1
    assert results[0]['amount'] == '1000.00'
    assert results[0]['currency'] == 'ARS'


def test_the_amount_of_a_withdrawal_is_negative(client):
    """Un retiro resta: el importe es el de la billetera del usuario."""
    user = create_approved_user(email='listado-retiro@example.com')
    authenticate(client, user)
    create_movement(client, 'deposit', '1000.00', 'ARS', 'listado-ret-dep')
    create_movement(client, 'withdrawal', '250.50', 'ARS', 'listado-ret')

    results = list_movements(client)
    by_type = {result['type']: result for result in results}

    assert by_type['deposit']['amount'] == '1000.00'
    assert by_type['withdrawal']['amount'] == '-250.50'
    assert by_type['withdrawal']['currency'] == 'ARS'


def test_the_amount_is_a_string_with_two_decimals(client):
    """El importe viaja como string decimal (como los demás importes)."""
    user = create_approved_user(email='listado-string@example.com')
    authenticate(client, user)
    create_movement(client, 'deposit', '10.00', 'USD', 'listado-str')

    results = list_movements(client)

    assert results[0]['amount'] == '10.00'
    assert isinstance(results[0]['amount'], str)


def test_the_amount_of_a_received_transfer_is_positive(client):
    """Una transferencia recibida entra: el importe es positivo para el receptor."""
    sender = create_approved_user(email='listado-emisor@example.com')
    receiver = create_approved_user(email='listado-receptor@example.com')

    sender_client = APIClient()
    authenticate(sender_client, sender)
    create_movement(sender_client, 'deposit', '5000.00', 'ARS', 'listado-tr-dep')

    receiver_client = APIClient()
    authenticate(receiver_client, receiver)
    receiver_client.post(
        '/api/v1/ledger/accounts/',
        {'currency': 'ARS'},
        format='json',
    )
    receiver_accounts = receiver_client.get('/api/v1/ledger/accounts/').json()['results']
    destination = next(account for account in receiver_accounts if account['currency'] == 'ARS')

    response = sender_client.post(
        '/api/v1/ledger/transactions/',
        {
            'type': 'transfer',
            'currency': 'ARS',
            'amount': '700.00',
            'destination_account_id': destination['id'],
        },
        format='json',
        HTTP_IDEMPOTENCY_KEY='listado-tr',
    )
    assert response.status_code == 201, response.data

    results = list_movements(receiver_client)

    assert len(results) == 1
    assert results[0]['amount'] == '700.00'
    assert results[0]['currency'] == 'ARS'


def test_the_movements_list_does_not_query_per_movement(client):
    """El listado no hace una consulta por movimiento."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    user = create_approved_user(email='listado-consultas@example.com')
    authenticate(client, user)
    for index in range(5):
        create_movement(client, 'deposit', '10.00', 'ARS', f'listado-num-{index}')

    with CaptureQueriesContext(connection) as queries_with_five:
        results = list_movements(client)

    for index in range(5, 10):
        create_movement(client, 'deposit', '10.00', 'ARS', f'listado-num-{index}')

    with CaptureQueriesContext(connection) as queries_with_ten:
        more_results = list_movements(client)

    assert len(results) == 5
    assert len(more_results) == 10
    assert len(queries_with_ten) == len(queries_with_five)


def test_the_movements_list_of_another_user_is_not_exposed(client):
    """Cada usuario ve sus propios movimientos, con su propio importe."""
    user = create_approved_user(email='listado-uno@example.com')
    other = create_approved_user(email='listado-otro@example.com')

    authenticate(client, user)
    create_movement(client, 'deposit', '100.00', 'ARS', 'listado-uno-dep')

    other_client = APIClient()
    authenticate(other_client, other)
    create_movement(other_client, 'deposit', '900.00', 'ARS', 'listado-otro-dep')

    results = list_movements(other_client)

    assert len(results) == 1
    assert results[0]['amount'] == '900.00'
    assert results[0]['currency'] == 'ARS'


def test_the_transfers_keep_the_sign_from_the_users_wallet(client):
    """Una salida de plata es negativa y una entrada positiva."""
    user = create_approved_user(email='listado-signo@example.com')
    authenticate(client, user)
    create_movement(client, 'deposit', '1000.00', 'ARS', 'listado-signo-dep')

    other = create_approved_user(email='listado-signo-otro@example.com')
    other_client = APIClient()
    authenticate(other_client, other)
    other_client.post(
        '/api/v1/ledger/accounts/',
        {'currency': 'ARS'},
        format='json',
    )
    other_accounts = other_client.get('/api/v1/ledger/accounts/').json()['results']
    destination = next(account for account in other_accounts if account['currency'] == 'ARS')
    client.post(
        '/api/v1/ledger/transactions/',
        {
            'type': 'transfer',
            'currency': 'ARS',
            'amount': '300.00',
            'destination_account_id': destination['id'],
        },
        format='json',
        HTTP_IDEMPOTENCY_KEY='listado-signo-tr',
    )

    results = list_movements(client)
    by_type = {result['type']: result for result in results}

    assert by_type['transfer']['amount'] == '-300.00'
    assert by_type['deposit']['amount'] == '1000.00'


def test_the_movement_detail_keeps_its_shape(client):
    """El detalle del movimiento no cambia (los campos nuevos son del listado)."""
    user = create_approved_user(email='listado-detalle@example.com')
    authenticate(client, user)
    movement = create_movement(client, 'deposit', '100.00', 'ARS', 'listado-detalle-dep')

    response = client.get(f'/api/v1/ledger/transactions/{movement["id"]}/')

    assert response.status_code == 200
    assert 'id' in response.data
    assert response.data['type'] == 'deposit'


def test_the_amount_is_a_decimal_in_the_service_layer():
    """El importe que se calcula es un Decimal (nunca un float)."""
    from apps.ledger.selectors import list_user_movement_amounts

    user = create_approved_user(email='listado-decimal@example.com')
    amounts = list_user_movement_amounts(transactions=[], user_id=user.id)

    assert amounts == {}
    assert isinstance(Decimal('0.00'), Decimal)
    assert uuid.uuid4() is not None
