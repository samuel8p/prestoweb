"""Tests del selector de movimientos del ledger en un rango."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from apps.ledger.tests.factories import create_approved_user

pytestmark = pytest.mark.django_db


def fund_user(user_id, amount='1000.00', currency='ARS', key='fund'):
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


def period(start='2026-10-01', end='2026-10-31'):
    """Devuelve el rango (inicio y fin) de un período en UTC."""
    from datetime import date

    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    return (
        datetime(start_date.year, start_date.month, start_date.day, tzinfo=UTC),
        datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, 999999, tzinfo=UTC),
    )


def test_list_transactions_in_period_returns_the_movements_of_the_period():
    """El selector devuelve los movimientos que caen en el rango."""
    from apps.ledger.selectors import list_transactions_in_period

    user = create_approved_user(email='rango@example.com')
    fund_user(user.id, key='rango-1')
    movement = make_withdrawal(user.id, key='rango-1-dentro')
    start, end = period()

    transactions = list_transactions_in_period(
        user_id=user.id,
        currency='ARS',
        start=start,
        end=end,
    )

    assert movement.id in {transaction.id for transaction in transactions}


def test_list_transactions_in_period_excludes_movements_outside_the_range():
    """Los movimientos que no caen en el rango quedan afuera.

    El ledger es inmutable: no se puede cambiar la fecha de un movimiento, así
    que el rango se prueba con un período que no incluye el momento actual.
    """
    from apps.ledger.selectors import list_transactions_in_period

    user = create_approved_user(email='rango-fuera@example.com')
    fund_user(user.id, key='rango-2')
    movement = make_withdrawal(user.id, key='rango-2-dentro')
    start, end = period('2020-01-01', '2020-01-31')

    transactions = list_transactions_in_period(
        user_id=user.id,
        currency='ARS',
        start=start,
        end=end,
    )

    assert movement.id not in {transaction.id for transaction in transactions}


def test_list_transactions_in_period_excludes_other_currencies():
    """Un movimiento en otra moneda no entra en el reporte."""
    from apps.ledger.selectors import list_transactions_in_period

    user = create_approved_user(email='rango-monedas@example.com')
    fund_user(user.id, key='rango-3')
    in_ars = make_withdrawal(user.id, currency='ARS', key='rango-3-ars')
    fund_user(user.id, currency='USD', key='rango-3-usd')
    in_usd = make_withdrawal(user.id, currency='USD', key='rango-3-usd-g')
    start, end = period()

    transactions = list_transactions_in_period(
        user_id=user.id,
        currency='ARS',
        start=start,
        end=end,
    )

    identifiers = {transaction.id for transaction in transactions}
    assert in_ars.id in identifiers
    assert in_usd.id not in identifiers


def test_list_transactions_in_period_excludes_other_users_movements():
    """El selector solo devuelve los movimientos del usuario."""
    from apps.ledger.selectors import list_transactions_in_period

    user = create_approved_user(email='rango-propio@example.com')
    other = create_approved_user(email='rango-ajeno@example.com')
    fund_user(other.id, key='rango-4')
    foreign = make_withdrawal(other.id, key='rango-4-ajeno')
    start, end = period()

    transactions = list_transactions_in_period(
        user_id=user.id,
        currency='ARS',
        start=start,
        end=end,
    )

    assert foreign.id not in {transaction.id for transaction in transactions}
