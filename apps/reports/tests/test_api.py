"""Tests de la API de reports."""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

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


def create_user(email='reportes@example.com'):
    """Crea un usuario con KYC aprobada."""
    from apps.identity.services import register_user, resolve_kyc, submit_kyc

    user = register_user(email=email, password='TestPass123!')
    verification = submit_kyc(user=user, documents={})
    resolve_kyc(
        verification_id=verification.id,
        status='approved',
        resolved_by_user_id=uuid.uuid4(),
    )
    return user


def fund_user(user_id, amount='10000.00', currency='ARS', key='fund'):
    """Deposita fondos simulados en la billetera del usuario."""
    from apps.ledger.services import deposit

    return deposit(
        user_id=user_id,
        currency=currency,
        amount=Decimal(amount),
        idempotency_key=key,
    )


def make_withdrawal(user_id, amount='100.00', currency='ARS', key='gasto'):
    """Retira fondos de la billetera del usuario."""
    from apps.ledger.services import withdraw

    return withdraw(
        user_id=user_id,
        currency=currency,
        amount=Decimal(amount),
        idempotency_key=key,
    )


def current_month_range():
    """Devuelve el rango ISO del mes calendario actual en UTC."""
    today = datetime.now(UTC).date()
    first = today.replace(day=1)
    if first.month == 12:
        next_month = date(first.year + 1, 1, 1)
    else:
        next_month = date(first.year, first.month + 1, 1)
    last = next_month - timedelta(days=1)
    return first.isoformat(), last.isoformat()


def test_movements_report_requires_authentication(client):
    """Sin token el reporte responde 401."""
    response = client.get('/api/v1/reports/movements/?currency=ARS')

    assert response.status_code == 401
    assert response.data['error']['code'] == 'not_authenticated'


def test_movements_report_requires_the_currency(client):
    """La moneda es obligatoria."""
    user = create_user(email='reportes-sin-moneda@example.com')
    authenticate(client, user)

    response = client.get('/api/v1/reports/movements/')

    assert response.status_code == 400
    assert response.data['error']['code'] == 'validation_error'


def test_movements_report_rejects_an_unknown_currency(client):
    """Una moneda que no es del proyecto responde 400."""
    user = create_user(email='reportes-moneda-invalida@example.com')
    authenticate(client, user)

    response = client.get('/api/v1/reports/movements/?currency=EUR')

    assert response.status_code == 400


def test_movements_report_rejects_a_range_longer_than_twelve_months(client):
    """Un rango de más de 12 meses responde 400."""
    user = create_user(email='reportes-rango-largo@example.com')
    authenticate(client, user)

    response = client.get('/api/v1/reports/movements/?currency=ARS&from=2024-01-01&to=2026-01-31')

    assert response.status_code == 400


def test_movements_report_rejects_from_after_to(client):
    """Un rango invertido responde 400."""
    user = create_user(email='reportes-rango-invertido@example.com')
    authenticate(client, user)

    response = client.get('/api/v1/reports/movements/?currency=ARS&from=2026-03-01&to=2026-01-01')

    assert response.status_code == 400


def test_movements_report_returns_the_movements_of_the_period(client):
    """El reporte devuelve los movimientos del usuario con su importe y su estado."""
    user = create_user(email='reportes-movimientos@example.com')
    authenticate(client, user)
    fund_user(user.id, key='reportes-1')
    movement = make_withdrawal(user.id, amount='100.50', key='reportes-1-gasto')
    start, end = current_month_range()

    response = client.get(
        f'/api/v1/reports/movements/?currency=ARS&from={start}&to={end}',
    )

    assert response.status_code == 200
    identifiers = [row['id'] for row in response.data['results']]
    assert str(movement.id) in identifiers
    row = next(row for row in response.data['results'] if row['id'] == str(movement.id))
    assert row['amount'] == '100.50'
    assert row['currency'] == 'ARS'
    assert row['type'] == 'withdrawal'
    assert row['is_reversed'] is False


def test_movements_report_marks_the_reversed_movements(client):
    """Un movimiento revertido aparece con `is_reversed` en true."""
    from apps.ledger.services import reverse_transaction

    user = create_user(email='reportes-revertido@example.com')
    authenticate(client, user)
    fund_user(user.id, key='reportes-2')
    movement = make_withdrawal(user.id, amount='25.00', key='reportes-2-gasto')
    reverse_transaction(transaction_id=movement.id, staff_user_id=user.id)
    start, end = current_month_range()

    response = client.get(
        f'/api/v1/reports/movements/?currency=ARS&from={start}&to={end}',
    )

    row = next(row for row in response.data['results'] if row['id'] == str(movement.id))
    assert row['is_reversed'] is True


def test_movements_report_does_not_show_other_users_movements(client):
    """Cada usuario ve solo sus movimientos."""
    user = create_user(email='reportes-ajeno@example.com')
    other = create_user(email='reportes-ajeno-otro@example.com')
    authenticate(client, user)
    fund_user(other.id, key='reportes-3')
    foreign = make_withdrawal(other.id, amount='99.00', key='reportes-3-gasto')
    start, end = current_month_range()

    response = client.get(
        f'/api/v1/reports/movements/?currency=ARS&from={start}&to={end}',
    )

    identifiers = [row['id'] for row in response.data['results']]
    assert str(foreign.id) not in identifiers
    assert all(row['id'] != str(foreign.id) for row in response.data['results'])


def test_movements_report_separates_currencies(client):
    """Un movimiento en USD no aparece en el reporte de ARS."""
    user = create_user(email='reportes-monedas@example.com')
    authenticate(client, user)
    fund_user(user.id, key='reportes-4-ars')
    in_ars = make_withdrawal(user.id, amount='10.00', currency='ARS', key='reportes-4-ars-g')
    fund_user(user.id, currency='USD', key='reportes-4-usd')
    in_usd = make_withdrawal(user.id, amount='20.00', currency='USD', key='reportes-4-usd-g')
    start, end = current_month_range()

    response = client.get(
        f'/api/v1/reports/movements/?currency=ARS&from={start}&to={end}',
    )

    identifiers = [row['id'] for row in response.data['results']]
    assert str(in_ars.id) in identifiers
    assert str(in_usd.id) not in identifiers
