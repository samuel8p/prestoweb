"""Tests de las reglas que definen si un movimiento es un gasto.

Las reglas se prueban sobre el detalle del movimiento ya resuelto, porque
algunas son **defensivas**: hay movimientos que la base no permite, como una
transferencia entre dos cuentas propias del mismo usuario (hay una billetera
por usuario y moneda).
"""

import uuid
from datetime import UTC, datetime, timezone
from decimal import Decimal

import pytest

pytestmark = pytest.mark.django_db

USER_ID = uuid.UUID('11111111-1111-1111-1111-111111111111')
OTHER_USER_ID = uuid.UUID('22222222-2222-2222-2222-222222222222')


def make_leg(
    account_kind='user_wallet',
    direction='debit',
    amount='100.00',
    currency='ARS',
    user_id=USER_ID,
):
    """Arma una pata de movimiento con los datos del detalle del ledger."""
    return {
        'account_id': uuid.uuid4(),
        'account_kind': account_kind,
        'account_user_id': user_id,
        'direction': direction,
        'amount': Decimal(amount),
        'currency': currency,
    }


def make_detail(legs, is_reversed=False):
    """Arma el detalle de un movimiento con los datos del selector del ledger."""
    return {
        'transaction_id': uuid.uuid4(),
        'type': 'transfer',
        'occurred_at': datetime(2026, 10, 21, tzinfo=UTC),
        'is_reversed': is_reversed,
        'legs': legs,
    }


def classify(detail, breakdown=None):
    """Clasifica un movimiento con la función pura de la app."""
    from apps.budgets.selectors import _classify_movement

    return _classify_movement(user_id=USER_ID, detail=detail, breakdown=breakdown)


def test_withdrawal_to_custody_is_an_expense():
    """Un retiro es un gasto: el dinero sale de la billetera hacia el exterior."""
    detail = make_detail(
        [
            make_leg(direction='debit', amount='100.00'),
            make_leg(account_kind='custody', direction='credit', user_id=None),
        ]
    )

    analysis = classify(detail)

    assert analysis['is_expense'] is True
    assert analysis['amount'] == Decimal('100.00')
    assert analysis['currency'] == 'ARS'


def test_transfer_to_another_user_is_an_expense():
    """Un pago a otra persona es un gasto del que paga."""
    detail = make_detail(
        [
            make_leg(direction='debit', amount='100.00'),
            make_leg(direction='credit', user_id=OTHER_USER_ID),
        ]
    )

    analysis = classify(detail)

    assert analysis['is_expense'] is True
    assert analysis['amount'] == Decimal('100.00')


def test_transfer_between_own_accounts_is_not_an_expense():
    """El dinero que se mueve entre cuentas propias no es un gasto."""
    detail = make_detail(
        [
            make_leg(direction='debit', amount='100.00'),
            make_leg(direction='credit', user_id=USER_ID),
        ]
    )

    analysis = classify(detail)

    assert analysis['is_expense'] is False
    assert analysis['amount'] is None


def test_investment_movement_is_not_an_expense():
    """El dinero que se convierte en inversión no es un gasto."""
    detail = make_detail(
        [
            make_leg(direction='debit', amount='5000.00'),
            make_leg(account_kind='system', direction='credit', user_id=None),
        ]
    )

    analysis = classify(detail)

    assert analysis['is_expense'] is False


def test_incoming_movement_is_not_an_expense():
    """Un movimiento que solo acredita la billetera no es un gasto."""
    detail = make_detail(
        [
            make_leg(direction='credit', amount='100.00'),
            make_leg(account_kind='custody', direction='debit', user_id=None),
        ]
    )

    analysis = classify(detail)

    assert analysis['is_visible'] is True
    assert analysis['is_expense'] is False


def test_reversed_movement_is_not_an_expense():
    """Un movimiento revertido no cuenta."""
    detail = make_detail(
        [
            make_leg(direction='debit', amount='100.00'),
            make_leg(account_kind='custody', direction='credit', user_id=None),
        ],
        is_reversed=True,
    )

    analysis = classify(detail)

    assert analysis['is_expense'] is False


def test_installment_payment_counts_only_the_interest():
    """El pago de una cuota cuenta solo por el interés: el capital es deuda."""
    detail = make_detail(
        [
            make_leg(direction='debit', amount='945.60'),
            make_leg(direction='credit', user_id=OTHER_USER_ID),
        ]
    )
    breakdown = {
        'kind': 'installment_payment',
        'principal': Decimal('800.00'),
        'interest': Decimal('145.60'),
        'currency': 'ARS',
    }

    analysis = classify(detail, breakdown=breakdown)

    assert analysis['is_expense'] is True
    assert analysis['amount'] == Decimal('145.60')


def test_installment_without_interest_is_not_an_expense():
    """Una cuota sin interés no suma nada al gasto."""
    detail = make_detail(
        [
            make_leg(direction='debit', amount='800.00'),
            make_leg(direction='credit', user_id=OTHER_USER_ID),
        ]
    )
    breakdown = {
        'kind': 'installment_payment',
        'principal': Decimal('800.00'),
        'interest': Decimal('0.00'),
        'currency': 'ARS',
    }

    analysis = classify(detail, breakdown=breakdown)

    assert analysis['is_expense'] is False


def test_loan_disbursement_is_not_an_expense():
    """El desembolso del préstamo convierte dinero en un activo."""
    detail = make_detail(
        [
            make_leg(direction='debit', amount='3000.00'),
            make_leg(direction='credit', user_id=OTHER_USER_ID),
        ]
    )
    breakdown = {
        'kind': 'loan_disbursement',
        'principal': Decimal('3000.00'),
        'interest': Decimal('0.00'),
        'currency': 'ARS',
    }

    analysis = classify(detail, breakdown=breakdown)

    assert analysis['is_expense'] is False


def test_movement_of_another_user_is_not_visible():
    """Un movimiento que no toca la billetera del usuario no es visible."""
    detail = make_detail(
        [
            make_leg(direction='debit', user_id=OTHER_USER_ID),
            make_leg(direction='credit', user_id=None),
        ]
    )

    analysis = classify(detail)

    assert analysis['is_visible'] is False
    assert analysis['is_expense'] is False
