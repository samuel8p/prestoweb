"""Tests de los selectores de detalle de movimientos del ledger."""

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


def test_get_movement_detail_returns_the_legs_with_their_account():
    """El detalle expone las patas del movimiento con cuenta, kind, dirección e importe."""
    from apps.ledger.models import Account
    from apps.ledger.selectors import get_movement_detail
    from apps.ledger.services import withdraw

    user = create_approved_user()
    fund_user(user.id, key='detalle-1')
    movement = withdraw(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='detalle-1-retiro',
    )

    detail = get_movement_detail(transaction_id=movement.id)

    assert detail is not None
    assert detail['transaction_id'] == movement.id
    assert detail['type'] == movement.type
    assert detail['is_reversed'] is False
    assert len(detail['legs']) == 2

    debit = next(leg for leg in detail['legs'] if leg['direction'] == 'debit')
    credit = next(leg for leg in detail['legs'] if leg['direction'] == 'credit')
    assert debit['account_user_id'] == user.id
    assert debit['account_kind'] == Account.Kind.USER_WALLET
    assert debit['amount'] == Decimal('100.00')
    assert debit['currency'] == Account.Currency.ARS
    assert credit['account_kind'] == Account.Kind.CUSTODY
    assert credit['account_user_id'] is None


def test_get_movement_detail_returns_none_for_unknown_movement():
    """Un movimiento inexistente no devuelve detalle."""
    import uuid

    from apps.ledger.selectors import get_movement_detail

    assert get_movement_detail(transaction_id=uuid.uuid4()) is None


def test_get_movement_detail_reports_that_the_movement_was_reversed():
    """Un movimiento revertido queda marcado como tal."""
    from apps.ledger.models import Account
    from apps.ledger.selectors import get_movement_detail
    from apps.ledger.services import reverse_transaction, withdraw

    user = create_approved_user()
    fund_user(user.id, key='detalle-2')
    movement = withdraw(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='detalle-2-retiro',
    )

    reverse_transaction(transaction_id=movement.id, staff_user_id=user.id)

    detail = get_movement_detail(transaction_id=movement.id)
    assert detail is not None
    assert detail['is_reversed'] is True


def test_list_movement_details_returns_every_movement_of_the_batch():
    """El selector por lotes devuelve el detalle de todos los movimientos pedidos."""
    from apps.ledger.models import Account
    from apps.ledger.selectors import list_movement_details
    from apps.ledger.services import withdraw

    user = create_approved_user()
    fund_user(user.id, key='detalle-3')
    first = withdraw(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('10.00'),
        idempotency_key='detalle-3-a',
    )
    second = withdraw(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('20.00'),
        idempotency_key='detalle-3-b',
    )

    details = list_movement_details(transaction_ids=[first.id, second.id])

    assert set(details) == {first.id, second.id}
    assert details[first.id]['legs'][0]['amount'] in (
        Decimal('10.00'),
        Decimal('20.00'),
    )


def test_list_movement_details_ignores_unknown_movements():
    """Los ids que no existen no aparecen en el resultado."""
    import uuid

    from apps.ledger.selectors import list_movement_details

    assert list_movement_details(transaction_ids=[uuid.uuid4()]) == {}


def test_list_movement_details_does_not_query_per_movement(django_assert_num_queries):
    """El lote resuelve todos los movimientos sin una consulta por movimiento."""
    from apps.ledger.models import Account
    from apps.ledger.selectors import list_movement_details
    from apps.ledger.services import withdraw

    user = create_approved_user()
    fund_user(user.id, key='detalle-4')
    movements = [
        withdraw(
            user_id=user.id,
            currency=Account.Currency.ARS,
            amount=Decimal('10.00'),
            idempotency_key=f'detalle-4-{index}',
        )
        for index in range(5)
    ]

    with django_assert_num_queries(3):
        details = list_movement_details(transaction_ids=[movement.id for movement in movements])

    assert len(details) == 5
