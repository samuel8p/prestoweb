"""Tests de los servicios de escritura de investments."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.investments.tests.factories import (
    InvestmentProductFactory,
    create_approved_user,
    fund_user,
)

pytestmark = pytest.mark.django_db


def test_open_position_creates_active_position():
    """Abrir una inversión crea la posición activa del usuario."""
    from apps.investments.models import Position
    from apps.investments.services import open_position

    user = create_approved_user()
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='inv-dep')

    position = open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='inv-1',
    )

    assert position.status == Position.Status.ACTIVE
    assert position.user_id == user.id
    assert position.amount == Decimal('5000.00')


def test_open_position_computes_simple_interest():
    """El interés se calcula al abrir con la tasa y el plazo del producto."""
    from apps.investments.services import open_position

    user = create_approved_user()
    product = InvestmentProductFactory(
        term_days=365,
        annual_rate_tna=Decimal('12.00'),
        min_amount=Decimal('1000.00'),
    )
    fund_user(user.id, amount='10000.00', key='inv-dep-2')

    position = open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='inv-2',
    )

    assert position.interest_amount == Decimal('600.00')


def test_open_position_sets_maturity_date():
    """La posición vence a los term_days del producto."""
    from apps.investments.services import open_position

    user = create_approved_user()
    product = InvestmentProductFactory(term_days=30, min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='inv-dep-3')

    position = open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='inv-3',
    )

    assert position.maturity_date == position.opened_at.date() + timedelta(days=30)


def test_open_position_moves_money_to_the_system_account():
    """El capital invertido sale de la billetera del usuario."""
    from apps.investments.services import open_position
    from apps.ledger.selectors import get_user_wallet

    user = create_approved_user()
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='inv-dep-4')

    open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='inv-4',
    )

    wallet = get_user_wallet(user_id=user.id, currency='ARS')
    assert wallet.balance == Decimal('5000.00')


def test_open_position_requires_approved_kyc():
    """Sin KYC aprobada no se puede invertir."""
    from apps.core.exceptions import KYCNotCompleted
    from apps.identity.services import register_user
    from apps.investments.services import open_position

    user = register_user(email='inv-sin-kyc@example.com', password='TestPass123!')
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))

    with pytest.raises(KYCNotCompleted):
        open_position(
            user_id=user.id,
            product_id=product.id,
            amount=Decimal('5000.00'),
            idempotency_key='inv-kyc',
        )


def test_open_position_rejects_unknown_product():
    """Un producto inexistente no se puede invertir."""
    from apps.investments.exceptions import ProductNotFound
    from apps.investments.services import open_position

    user = create_approved_user()
    fund_user(user.id, amount='10000.00', key='inv-dep-5')

    with pytest.raises(ProductNotFound):
        open_position(
            user_id=user.id,
            product_id=uuid.uuid4(),
            amount=Decimal('5000.00'),
            idempotency_key='inv-unknown',
        )


def test_open_position_rejects_inactive_product():
    """Un producto cancelado no admite nuevas inversiones."""
    from apps.investments.exceptions import ProductNotActive
    from apps.investments.models import InvestmentProduct
    from apps.investments.services import open_position

    user = create_approved_user()
    product = InvestmentProductFactory(
        min_amount=Decimal('1000.00'),
        status=InvestmentProduct.Status.CANCELLED,
    )
    fund_user(user.id, amount='10000.00', key='inv-dep-6')

    with pytest.raises(ProductNotActive):
        open_position(
            user_id=user.id,
            product_id=product.id,
            amount=Decimal('5000.00'),
            idempotency_key='inv-inactive',
        )


def test_open_position_rejects_amount_below_minimum():
    """El monto debe ser igual o mayor al mínimo del producto."""
    from apps.investments.exceptions import InsufficientInvestmentAmount
    from apps.investments.services import open_position

    user = create_approved_user()
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='inv-dep-7')

    with pytest.raises(InsufficientInvestmentAmount):
        open_position(
            user_id=user.id,
            product_id=product.id,
            amount=Decimal('500.00'),
            idempotency_key='inv-min',
        )


def test_open_position_rejects_different_currency():
    """La moneda de la inversión debe ser la del producto."""
    from apps.investments.services import open_position
    from apps.ledger.exceptions import CurrencyMismatch

    user = create_approved_user()
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='inv-dep-8')

    with pytest.raises(CurrencyMismatch):
        open_position(
            user_id=user.id,
            product_id=product.id,
            amount=Decimal('5000.00'),
            idempotency_key='inv-currency',
            currency='USD',
        )


def test_open_position_is_idempotent():
    """La misma clave de idempotencia devuelve la posición original."""
    from apps.investments.models import Position
    from apps.investments.services import open_position

    user = create_approved_user()
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='inv-dep-9')

    first = open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='inv-idem',
    )
    second = open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='inv-idem',
    )

    assert first.id == second.id
    assert Position.objects.count() == 1


def test_open_position_same_key_different_product_raises_conflict():
    """La misma clave con otro producto devuelve conflicto."""
    from apps.investments.services import open_position
    from apps.ledger.exceptions import IdempotencyConflict

    user = create_approved_user()
    first_product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    second_product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='20000.00', key='inv-dep-10')

    open_position(
        user_id=user.id,
        product_id=first_product.id,
        amount=Decimal('5000.00'),
        idempotency_key='inv-conflict',
    )

    with pytest.raises(IdempotencyConflict):
        open_position(
            user_id=user.id,
            product_id=second_product.id,
            amount=Decimal('5000.00'),
            idempotency_key='inv-conflict',
        )


def test_open_position_rolls_back_without_balance():
    """Si el usuario no tiene saldo, no queda posición ni movimiento."""
    from apps.core.exceptions import InsufficientFunds
    from apps.investments.models import Position
    from apps.investments.services import open_position
    from apps.ledger.selectors import get_user_wallet

    user = create_approved_user()
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))

    with pytest.raises(InsufficientFunds):
        open_position(
            user_id=user.id,
            product_id=product.id,
            amount=Decimal('5000.00'),
            idempotency_key='inv-sin-plata',
        )

    assert Position.objects.count() == 0
    wallet = get_user_wallet(user_id=user.id, currency='ARS')
    assert wallet is None or wallet.balance == Decimal('0.00')


def test_settle_matured_positions_pays_capital_and_interest():
    """Al liquidar se pagan el capital y el interés."""
    from apps.investments.services import open_position, settle_matured_positions
    from apps.ledger.selectors import get_user_wallet

    user = create_approved_user()
    product = InvestmentProductFactory(
        term_days=365,
        annual_rate_tna=Decimal('12.00'),
        min_amount=Decimal('1000.00'),
    )
    fund_user(user.id, amount='10000.00', key='inv-dep-11')
    position = open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='inv-settle',
    )

    settled = settle_matured_positions(today=date(2030, 1, 1))

    wallet = get_user_wallet(user_id=user.id, currency='ARS')
    assert settled == 1
    assert wallet.balance == Decimal('10600.00')
    assert position.interest_amount == Decimal('600.00')


def test_settle_matured_positions_marks_the_position_as_matured():
    """La posición liquidada pasa a matured."""
    from apps.investments.models import Position
    from apps.investments.services import open_position, settle_matured_positions

    user = create_approved_user()
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='inv-dep-12')
    position = open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='inv-settle-2',
    )

    settle_matured_positions(today=date(2030, 1, 1))

    position.refresh_from_db()
    assert position.status == Position.Status.MATURED


def test_settle_matured_positions_is_idempotent():
    """Liquidar dos veces no duplica el pago."""
    from apps.investments.services import open_position, settle_matured_positions
    from apps.ledger.selectors import get_user_wallet

    user = create_approved_user()
    product = InvestmentProductFactory(
        term_days=365,
        annual_rate_tna=Decimal('12.00'),
        min_amount=Decimal('1000.00'),
    )
    fund_user(user.id, amount='10000.00', key='inv-dep-13')
    open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='inv-settle-3',
    )

    first = settle_matured_positions(today=date(2030, 1, 1))
    second = settle_matured_positions(today=date(2030, 1, 1))

    wallet = get_user_wallet(user_id=user.id, currency='ARS')
    assert first == 1
    assert second == 0
    assert wallet.balance == Decimal('10600.00')


def test_settle_matured_positions_ignores_positions_not_matured():
    """Una posición que no venció no se liquida."""
    from apps.investments.services import open_position, settle_matured_positions
    from apps.ledger.selectors import get_user_wallet

    user = create_approved_user()
    product = InvestmentProductFactory(term_days=3650, min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='inv-dep-14')
    open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='inv-settle-4',
    )

    settled = settle_matured_positions(today=date(2030, 1, 1))

    wallet = get_user_wallet(user_id=user.id, currency='ARS')
    assert settled == 0
    assert wallet.balance == Decimal('5000.00')


def test_settle_registers_an_interest_movement():
    """El interés se liquida con un movimiento de tipo interest."""
    from apps.investments.services import open_position, settle_matured_positions
    from apps.ledger.selectors import list_transactions_for_user

    user = create_approved_user()
    product = InvestmentProductFactory(
        term_days=30,
        annual_rate_tna=Decimal('12.00'),
        min_amount=Decimal('1000.00'),
    )
    fund_user(user.id, amount='10000.00', key='inv-dep-15')
    open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='inv-settle-5',
    )

    settle_matured_positions(today=date(2030, 1, 1))

    movements = [
        transaction
        for transaction in list_transactions_for_user(user_id=user.id)
        if transaction.type == 'interest'
    ]
    assert len(movements) == 1
    credits = movements[0].entries.filter(direction='credit')
    assert sum(entry.amount for entry in credits) == Decimal('49.32')
