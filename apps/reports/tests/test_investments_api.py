"""Tests de la API de reports: inversiones."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.reports.tests.test_api import create_user, fund_user

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


def create_product(term_days=365, rate='12.00', min_amount='1000.00', currency='ARS'):
    """Crea un producto de plazo fijo activo."""
    from apps.investments.tests.factories import InvestmentProductFactory

    return InvestmentProductFactory(
        term_days=term_days,
        annual_rate_tna=Decimal(rate),
        min_amount=Decimal(min_amount),
        currency=currency,
    )


def open_position(user, product, amount='5000.00', key='inversion'):
    """Abre una posición de plazo fijo para el usuario."""
    from apps.investments.services import open_position

    return open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal(amount),
        idempotency_key=key,
    )


def test_investments_report_requires_authentication(client):
    """Sin token el reporte responde 401."""
    response = client.get('/api/v1/reports/investments/?currency=ARS')

    assert response.status_code == 401


def test_investments_report_requires_the_currency(client):
    """La moneda es obligatoria."""
    user = create_user(email='inversiones-sin-moneda@example.com')
    authenticate(client, user)

    response = client.get('/api/v1/reports/investments/')

    assert response.status_code == 400


def test_investments_report_shows_the_invested_capital_and_the_expected_interest(client):
    """El reporte muestra el capital invertido y el interés esperado."""
    user = create_user(email='inversiones@example.com')
    authenticate(client, user)
    product = create_product()
    fund_user(user.id, key='inversiones-1')
    position = open_position(user, product, key='inversiones-1')

    response = client.get('/api/v1/reports/investments/?currency=ARS')

    assert response.status_code == 200
    assert response.data['currency'] == 'ARS'
    assert response.data['total_invested'] == '5000.00'
    assert response.data['interest_expected'] == '600.00'
    assert response.data['interest_earned'] == '0.00'
    assert len(response.data['positions']) == 1
    row = response.data['positions'][0]
    assert row['position_id'] == str(position.id)
    assert row['product_id'] == str(product.id)
    assert row['amount'] == '5000.00'
    assert row['status'] == 'active'


def test_investments_report_shows_the_interest_earned_after_the_settlement(client):
    """Una posición liquidada suma el interés ganado y sale del capital invertido."""
    from apps.investments.services import settle_matured_positions

    user = create_user(email='inversiones-liquidadas@example.com')
    authenticate(client, user)
    product = create_product()
    fund_user(user.id, key='inversiones-2')
    open_position(user, product, key='inversiones-2')
    settle_matured_positions(today=date(2030, 1, 1))

    response = client.get('/api/v1/reports/investments/?currency=ARS')

    assert response.data['total_invested'] == '0.00'
    assert response.data['interest_expected'] == '0.00'
    assert response.data['interest_earned'] == '600.00'
    assert response.data['positions'][0]['status'] == 'matured'


def test_investments_report_separates_currencies(client):
    """Una posición en USD no aparece en el reporte de ARS."""
    user = create_user(email='inversiones-monedas@example.com')
    authenticate(client, user)
    product = create_product(currency='USD')
    fund_user(user.id, currency='USD', key='inversiones-3')
    open_position(user, product, key='inversiones-3')

    response = client.get('/api/v1/reports/investments/?currency=ARS')

    assert response.data['total_invested'] == '0.00'
    assert response.data['positions'] == []

    response_usd = client.get('/api/v1/reports/investments/?currency=USD')

    assert response_usd.data['total_invested'] == '5000.00'


def test_investments_report_does_not_show_other_users_positions(client):
    """Cada usuario ve solo sus posiciones."""
    user = create_user(email='inversiones-ajeno@example.com')
    other = create_user(email='inversiones-ajeno-otro@example.com')
    authenticate(client, user)
    product = create_product()
    fund_user(other.id, key='inversiones-4')
    open_position(other, product, key='inversiones-4')

    response = client.get('/api/v1/reports/investments/?currency=ARS')

    assert response.data['total_invested'] == '0.00'
    assert response.data['positions'] == []
