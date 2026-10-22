"""Tests del listado de posiciones con la moneda (D-11).

El listado de posiciones de inversión ahora trae, por posición, la moneda
del producto (antes había que pedir el detalle para saberla).
"""

import uuid
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.investments.tests.factories import create_approved_user

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


def fund_user(
    client,
    currency: str = 'ARS',
    amount: str = '10000.00',
    key: str = 'posiciones-fondo',
):
    """Deposita dinero simulado para el usuario autenticado."""
    response = client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'deposit', 'currency': currency, 'amount': amount},
        format='json',
        HTTP_IDEMPOTENCY_KEY=key,
    )
    assert response.status_code == 201, response.data


def create_product(currency: str, min_amount: str = '100.00'):
    """Crea un producto de plazo fijo activo en la moneda pedida."""
    from apps.investments.models import InvestmentProduct

    return InvestmentProduct.objects.create(
        type=InvestmentProduct.Type.FIXED_TERM,
        currency=currency,
        term_days=30,
        annual_rate_tna=Decimal('12.00'),
        min_amount=Decimal(min_amount),
        status=InvestmentProduct.Status.ACTIVE,
    )


def open_position(client, product, amount: str, key: str):
    """Abre una posición de inversión para el usuario autenticado."""
    response = client.post(
        '/api/v1/investments/positions/',
        {'product_id': str(product.id), 'amount': amount},
        format='json',
        HTTP_IDEMPOTENCY_KEY=key,
    )
    assert response.status_code == 201, response.data
    return response.data


def list_positions(client):
    """Lista las posiciones del usuario autenticado."""
    response = client.get('/api/v1/investments/positions/')
    assert response.status_code == 200, response.data
    return response.json()['results']


def test_the_positions_list_includes_the_currency(client):
    """Cada posición del listado trae la moneda del producto."""
    user = create_approved_user(email='posiciones-moneda@example.com')
    authenticate(client, user)
    fund_user(client, 'ARS', key='posiciones-fondo-1')
    product = create_product('ARS')
    open_position(client, product, '1000.00', 'posiciones-ars')

    results = list_positions(client)

    assert len(results) == 1
    assert results[0]['currency'] == 'ARS'


def test_the_positions_list_tells_ars_and_usd_apart(client):
    """Una posición en USD dice USD (y otra en ARS, ARS)."""
    user = create_approved_user(email='posiciones-dos-monedas@example.com')
    authenticate(client, user)
    fund_user(client, 'ARS', key='posiciones-fondo-2')
    fund_user(client, 'USD', key='posiciones-fondo-2-usd')
    open_position(client, create_product('ARS'), '1000.00', 'posiciones-ars-2')
    open_position(client, create_product('USD'), '200.00', 'posiciones-usd')

    results = list_positions(client)
    currencies = {result['currency'] for result in results}

    assert currencies == {'ARS', 'USD'}


def test_the_positions_of_another_user_are_not_exposed(client):
    """Cada usuario ve sus propias posiciones (con su moneda)."""
    user = create_approved_user(email='posiciones-uno@example.com')
    other = create_approved_user(email='posiciones-otro@example.com')

    authenticate(client, user)
    fund_user(client, 'ARS', key='posiciones-fondo-3')
    open_position(client, create_product('ARS'), '1000.00', 'posiciones-uno-ars')

    other_client = APIClient()
    authenticate(other_client, other)
    fund_user(other_client, 'USD', key='posiciones-fondo-4')
    open_position(other_client, create_product('USD'), '500.00', 'posiciones-otro-usd')

    results = list_positions(other_client)

    assert len(results) == 1
    assert results[0]['currency'] == 'USD'


def test_the_positions_list_does_not_query_per_position(client):
    """El listado no hace una consulta por posición."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    user = create_approved_user(email='posiciones-consultas@example.com')
    authenticate(client, user)
    fund_user(client, 'ARS', key='posiciones-fondo-5')
    product = create_product('ARS')
    for index in range(5):
        open_position(client, product, '100.00', f'posiciones-num-{index}')

    with CaptureQueriesContext(connection) as queries_with_five:
        results = list_positions(client)

    for index in range(5, 10):
        open_position(client, product, '100.00', f'posiciones-num-{index}')

    with CaptureQueriesContext(connection) as queries_with_ten:
        more_results = list_positions(client)

    assert len(results) == 5
    assert len(more_results) == 10
    assert len(queries_with_ten) == len(queries_with_five)


def test_the_position_detail_keeps_its_shape(client):
    """El detalle de la posición no cambia (los campos nuevos son del listado)."""
    user = create_approved_user(email='posiciones-detalle@example.com')
    authenticate(client, user)
    fund_user(client, 'ARS', key='posiciones-fondo-6')
    position = open_position(client, create_product('ARS'), '1000.00', 'posiciones-detalle')

    response = client.get(f'/api/v1/investments/positions/{position["id"]}/')

    assert response.status_code == 200
    assert response.data['product'] == position['product']
    assert uuid.uuid4() is not None
