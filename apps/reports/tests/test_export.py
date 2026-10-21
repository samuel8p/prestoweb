"""Tests de la exportación CSV de los reportes."""

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


def make_withdrawal(user_id, amount='100.00', currency='ARS', key='gasto', description=''):
    """Retira fondos de la billetera del usuario."""
    from apps.ledger.services import withdraw

    return withdraw(
        user_id=user_id,
        currency=currency,
        amount=Decimal(amount),
        idempotency_key=key,
        description=description,
    )


def test_csv_export_returns_a_csv_attachment(client):
    """La exportación devuelve un CSV descargable."""
    user = create_user(email='csv@example.com')
    authenticate(client, user)

    response = client.get('/api/v1/reports/movements/?currency=ARS&export=csv')

    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv; charset=utf-8'
    assert response['Content-Disposition'] == 'attachment; filename="reporte-movimientos.csv"'
    header = response.content.decode().splitlines()[0]
    assert header.split(',')[0] == 'id'


def test_csv_export_neutralizes_formula_injection(client):
    """Una celda que empieza con =, +, - o @ no se abre como fórmula."""
    user = create_user(email='csv-formula@example.com')
    authenticate(client, user)
    fund_user(user.id, key='csv-1')
    make_withdrawal(user.id, key='csv-1-g', description='=SUM(A1:A9)')

    response = client.get('/api/v1/reports/movements/?currency=ARS&export=csv')

    body = response.content.decode()
    assert "'=SUM(A1:A9)" in body
    assert '=SUM(A1:A9),' not in body.replace("'=SUM(A1:A9)", '')


def test_csv_export_of_the_spending_report(client):
    """El CSV del reporte de spending trae una fila por categoría."""
    from apps.budgets.services import categorize_movement, create_category

    user = create_user(email='csv-spending@example.com')
    authenticate(client, user)
    category = create_category(user_id=user.id, name='Comida')
    fund_user(user.id, key='csv-2')
    movement = make_withdrawal(user.id, amount='42.50', key='csv-2-g')
    categorize_movement(
        user_id=user.id,
        ledger_transaction_id=movement.id,
        category_id=category.id,
    )

    response = client.get('/api/v1/reports/spending/?currency=ARS&export=csv')

    assert response.status_code == 200
    assert response['Content-Disposition'] == 'attachment; filename="reporte-gasto.csv"'
    body = response.content.decode()
    assert 'category_id' in body
    assert 'Comida' in body
    assert '42.50' in body


def test_csv_export_of_the_loans_report(client):
    """El CSV del reporte de préstamos trae una fila por rol."""
    from apps.loans.services import accept_offer
    from apps.offers.services import create_offer

    user = create_user(email='csv-prestamos@example.com')
    lender = create_user(email='csv-prestamos-prestamista@example.com')
    authenticate(client, user)
    fund_user(lender.id, key='csv-3')
    offer = create_offer(
        lender_user_id=lender.id,
        amount=Decimal('3000.00'),
        currency='ARS',
        interest_rate=Decimal('24.00'),
        term_months=3,
    )
    accept_offer(
        borrower_user_id=user.id,
        offer_id=offer.id,
        idempotency_key='csv-3-aceptar',
    )

    response = client.get('/api/v1/reports/loans/?currency=ARS&export=csv')

    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv; charset=utf-8'
    body = response.content.decode()
    assert 'as_borrower' in body
    assert 'as_lender' in body


def test_csv_export_of_the_investments_report(client):
    """El CSV del reporte de inversiones trae una fila por posición."""
    from apps.investments.services import open_position
    from apps.investments.tests.factories import InvestmentProductFactory

    user = create_user(email='csv-inversiones@example.com')
    authenticate(client, user)
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, key='csv-4')
    open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='csv-4-inversion',
    )

    response = client.get('/api/v1/reports/investments/?currency=ARS&export=csv')

    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv; charset=utf-8'
    body = response.content.decode()
    assert 'position_id' in body
    assert '5000.00' in body


def test_csv_export_rejects_a_report_over_the_row_limit(client, monkeypatch):
    """Si el reporte supera el tope de filas, la exportación responde 400."""
    from apps.reports import export

    monkeypatch.setattr(export, 'MAX_EXPORT_ROWS', 2)
    user = create_user(email='csv-tope@example.com')
    authenticate(client, user)
    fund_user(user.id, key='csv-5')
    for index in range(3):
        make_withdrawal(user.id, amount='10.00', key=f'csv-5-{index}')

    response = client.get('/api/v1/reports/movements/?currency=ARS&export=csv')

    assert response.status_code == 400
    assert response.data['error']['code'] == 'validation_error'


def test_export_parameter_with_an_unknown_value_returns_400(client):
    """Un valor de `export` que no es `csv` es un error."""
    user = create_user(email='csv-desconocido@example.com')
    authenticate(client, user)

    response = client.get('/api/v1/reports/movements/?currency=ARS&export=xlsx')

    assert response.status_code == 400
