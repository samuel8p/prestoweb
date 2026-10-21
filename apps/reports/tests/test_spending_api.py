"""Tests de la API de reports: spending."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.reports.tests.test_api import create_user, current_month_range, fund_user, make_withdrawal

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


def create_category(user, name='Comida'):
    """Crea una categoría de gasto del usuario."""
    from apps.budgets.services import create_category

    return create_category(user_id=user.id, name=name)


def categorize(user, category, movement):
    """Categoriza un movimiento del ledger como gasto."""
    from apps.budgets.services import categorize_movement

    return categorize_movement(
        user_id=user.id,
        ledger_transaction_id=movement.id,
        category_id=category.id,
    )


def test_spending_report_requires_authentication(client):
    """Sin token el reporte responde 401."""
    response = client.get('/api/v1/reports/spending/?currency=ARS')

    assert response.status_code == 401


def test_spending_report_requires_the_currency(client):
    """La moneda es obligatoria."""
    user = create_user(email='gasto-sin-moneda@example.com')
    authenticate(client, user)

    response = client.get('/api/v1/reports/spending/')

    assert response.status_code == 400


def test_spending_report_returns_the_spending_per_category(client):
    """El reporte agrupa el gasto por categoría y devuelve el total."""
    user = create_user(email='gasto-categorias@example.com')
    authenticate(client, user)
    category = create_category(user, name='Comida')
    fund_user(user.id, key='gasto-1')
    movement = make_withdrawal(user.id, amount='100.50', key='gasto-1-a')
    other = make_withdrawal(user.id, amount='50.25', key='gasto-1-b')
    categorize(user, category, movement)
    categorize(user, category, other)
    start, end = current_month_range()

    response = client.get(f'/api/v1/reports/spending/?currency=ARS&from={start}&to={end}')

    assert response.status_code == 200
    assert response.data['currency'] == 'ARS'
    assert response.data['total'] == '150.75'
    assert len(response.data['categories']) == 1
    row = response.data['categories'][0]
    assert row['category_id'] == str(category.id)
    assert row['category_name'] == 'Comida'
    assert row['amount'] == '150.75'
    assert row['movements'] == 2


def test_spending_report_ignores_movements_without_a_category(client):
    """Un movimiento sin categoría no cuenta en el reporte."""
    user = create_user(email='gasto-sin-categoria@example.com')
    authenticate(client, user)
    create_category(user, name='Comida')
    fund_user(user.id, key='gasto-2')
    make_withdrawal(user.id, amount='900.00', key='gasto-2-sin-categoria')
    start, end = current_month_range()

    response = client.get(f'/api/v1/reports/spending/?currency=ARS&from={start}&to={end}')

    assert response.data['total'] == '0.00'
    assert response.data['categories'] == []


def test_spending_report_ignores_the_movements_outside_the_period(client):
    """Un movimiento fuera del rango no cuenta.

    El ledger es inmutable: no se puede fechar un movimiento en el pasado, así
    que el período se prueba con un rango que no incluye el momento actual.
    """
    user = create_user(email='gasto-fuera-de-rango@example.com')
    authenticate(client, user)
    category = create_category(user, name='Comida')
    fund_user(user.id, key='gasto-3')
    movement = make_withdrawal(user.id, amount='120.00', key='gasto-3-gasto')
    categorize(user, category, movement)

    response = client.get('/api/v1/reports/spending/?currency=ARS&from=2020-01-01&to=2020-01-31')

    assert response.status_code == 200
    assert response.data['total'] == '0.00'
    assert response.data['categories'] == []


def test_spending_report_separates_currencies(client):
    """Un gasto en USD no cuenta en el reporte de ARS."""
    user = create_user(email='gasto-monedas@example.com')
    authenticate(client, user)
    category = create_category(user, name='Comida')
    fund_user(user.id, key='gasto-4-ars')
    in_ars = make_withdrawal(user.id, amount='10.00', currency='ARS', key='gasto-4-ars-g')
    fund_user(user.id, currency='USD', key='gasto-4-usd')
    in_usd = make_withdrawal(user.id, amount='20.00', currency='USD', key='gasto-4-usd-g')
    categorize(user, category, in_ars)
    categorize(user, category, in_usd)
    start, end = current_month_range()

    response = client.get(f'/api/v1/reports/spending/?currency=ARS&from={start}&to={end}')

    assert response.data['total'] == '10.00'

    response_usd = client.get(f'/api/v1/reports/spending/?currency=USD&from={start}&to={end}')

    assert response_usd.data['total'] == '20.00'


def test_spending_report_does_not_show_other_users_data(client):
    """Cada usuario ve solo su gasto."""
    user = create_user(email='gasto-ajeno@example.com')
    other = create_user(email='gasto-ajeno-otro@example.com')
    authenticate(client, user)
    create_category(user, name='Comida')
    other_category = create_category(other, name='Ajena')
    fund_user(other.id, key='gasto-5')
    foreign = make_withdrawal(other.id, amount='700.00', key='gasto-5-ajeno')
    categorize(other, other_category, foreign)
    start, end = current_month_range()

    response = client.get(f'/api/v1/reports/spending/?currency=ARS&from={start}&to={end}')

    assert response.data['total'] == '0.00'
    assert response.data['categories'] == []


def test_spending_report_defaults_to_the_current_month(client):
    """Sin rango, el reporte cubre el mes calendario actual en UTC."""
    user = create_user(email='gasto-mes-actual@example.com')
    authenticate(client, user)
    category = create_category(user, name='Comida')
    fund_user(user.id, key='gasto-6')
    movement = make_withdrawal(user.id, amount='33.33', key='gasto-6-gasto')
    categorize(user, category, movement)

    response = client.get('/api/v1/reports/spending/?currency=ARS')

    assert response.status_code == 200
    assert response.data['total'] == '33.33'
    today = datetime.now(UTC).date()
    assert response.data['from_date'] == today.replace(day=1).isoformat()
