"""Tests del service de categorización de movimientos como gastos."""

from decimal import Decimal

import pytest

from apps.budgets.tests.factories import CategoryFactory, create_approved_user

pytestmark = pytest.mark.django_db


def fund_user(user_id, amount='10000.00', currency='ARS', key='fund'):
    """Deposita fondos simulados en la billetera del usuario."""
    from apps.ledger.services import deposit

    return deposit(
        user_id=user_id,
        currency=currency,
        amount=Decimal(amount),
        idempotency_key=key,
    )


def make_withdrawal(user_id, amount='100.00', key='retiro'):
    """Retira fondos de la billetera del usuario."""
    from apps.ledger.services import withdraw

    return withdraw(
        user_id=user_id,
        currency='ARS',
        amount=Decimal(amount),
        idempotency_key=key,
    )


def test_categorize_movement_links_the_movement_to_the_category():
    """La categorización registra el movimiento con su categoría."""
    from apps.budgets.services import categorize_movement

    user = create_approved_user(email='categorizar@example.com')
    user_id = user.id
    category = CategoryFactory(user_id=user_id)
    fund_user(user_id, key='cat-1')
    movement = make_withdrawal(user_id, key='cat-1-retiro')

    expense = categorize_movement(
        user_id=user_id,
        ledger_transaction_id=movement.id,
        category_id=category.id,
    )

    assert str(expense.user_id) == str(user_id)
    assert expense.category_id == category.id
    assert expense.ledger_transaction_id == movement.id


def test_categorize_movement_rejects_a_category_of_another_user():
    """No se puede categorizar con una categoría ajena."""
    from apps.budgets.exceptions import CategoryNotFound
    from apps.budgets.services import categorize_movement

    user = create_approved_user(email='categorizar@example.com')
    user_id = user.id
    other_category = CategoryFactory()
    fund_user(user_id, key='cat-2')
    movement = make_withdrawal(user_id, key='cat-2-retiro')

    with pytest.raises(CategoryNotFound):
        categorize_movement(
            user_id=user_id,
            ledger_transaction_id=movement.id,
            category_id=other_category.id,
        )


def test_categorize_movement_rejects_an_unknown_movement():
    """Un movimiento que no existe no se puede categorizar."""
    import uuid

    from apps.budgets.exceptions import MovementNotFound
    from apps.budgets.services import categorize_movement

    category = CategoryFactory()

    with pytest.raises(MovementNotFound):
        categorize_movement(
            user_id=category.user_id,
            ledger_transaction_id=uuid.uuid4(),
            category_id=category.id,
        )


def test_categorize_movement_rejects_a_movement_of_another_user():
    """Un movimiento de otro usuario no es visible."""
    from apps.budgets.exceptions import MovementNotFound
    from apps.budgets.services import categorize_movement

    other = create_approved_user(email='ajeno-categorizar@example.com')
    category = CategoryFactory()
    fund_user(other.id, key='cat-3-ajeno')
    movement = make_withdrawal(other.id, key='cat-3-ajeno-retiro')

    with pytest.raises(MovementNotFound):
        categorize_movement(
            user_id=category.user_id,
            ledger_transaction_id=movement.id,
            category_id=category.id,
        )


def test_categorize_movement_rejects_a_deposit():
    """Un depósito no es un gasto: es dinero que entra."""
    from apps.budgets.exceptions import NotAnExpense
    from apps.budgets.services import categorize_movement

    user = create_approved_user(email='categorizar@example.com')
    user_id = user.id
    category = CategoryFactory(user_id=user_id)
    movement = fund_user(user_id, key='cat-4')

    with pytest.raises(NotAnExpense):
        categorize_movement(
            user_id=user_id,
            ledger_transaction_id=movement.id,
            category_id=category.id,
        )


def test_categorize_movement_rejects_an_investment_movement():
    """El dinero que se convierte en inversión no es un gasto."""
    from apps.budgets.exceptions import NotAnExpense
    from apps.budgets.services import categorize_movement
    from apps.ledger.services import SYSTEM_COUNTERPART, transfer_to_counterpart

    user = create_approved_user(email='categorizar@example.com')
    user_id = user.id
    category = CategoryFactory(user_id=user_id)
    fund_user(user_id, key='cat-5')
    movement = transfer_to_counterpart(
        user_id=user_id,
        counterparty_kind=SYSTEM_COUNTERPART,
        currency='ARS',
        amount=Decimal('5000.00'),
        idempotency_key='cat-5-inversion',
        initiated_by_user_id=user_id,
    )

    with pytest.raises(NotAnExpense):
        categorize_movement(
            user_id=user_id,
            ledger_transaction_id=movement.id,
            category_id=category.id,
        )


def test_categorize_movement_rejects_the_loan_disbursement():
    """El desembolso del préstamo convierte dinero en un activo: no es un gasto."""
    from apps.budgets.exceptions import NotAnExpense
    from apps.budgets.services import categorize_movement
    from apps.loans.services import accept_offer
    from apps.offers.services import create_offer

    lender = create_approved_user(email='prestamista-desembolso@example.com')
    borrower = create_approved_user(email='prestatario-desembolso@example.com')
    offer = create_offer(
        lender_user_id=lender.id,
        amount=Decimal('3000.00'),
        currency='ARS',
        interest_rate=Decimal('24.00'),
        term_months=3,
    )
    fund_user(lender.id, key='cat-6')
    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='cat-6-aceptar',
    )
    category = CategoryFactory(user_id=lender.id)

    with pytest.raises(NotAnExpense):
        categorize_movement(
            user_id=lender.id,
            ledger_transaction_id=loan.ledger_transaction_id,
            category_id=category.id,
        )


def test_categorize_movement_accepts_a_loan_installment_payment():
    """El pago de una cuota se puede categorizar: solo cuenta el interés."""
    from apps.budgets.services import categorize_movement
    from apps.loans.services import accept_offer, pay_installment
    from apps.offers.services import create_offer

    lender = create_approved_user(email='prestamista-cuota@example.com')
    borrower = create_approved_user(email='prestatario-cuota@example.com')
    offer = create_offer(
        lender_user_id=lender.id,
        amount=Decimal('3000.00'),
        currency='ARS',
        interest_rate=Decimal('24.00'),
        term_months=3,
    )
    fund_user(lender.id, key='cat-7')
    fund_user(borrower.id, key='cat-7-prestatario')
    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='cat-7-aceptar',
    )
    installment = pay_installment(
        loan_id=loan.id,
        number=1,
        borrower_user_id=borrower.id,
    )
    category = CategoryFactory(user_id=borrower.id)

    expense = categorize_movement(
        user_id=borrower.id,
        ledger_transaction_id=installment.ledger_transaction_id,
        category_id=category.id,
    )

    assert expense.ledger_transaction_id == installment.ledger_transaction_id


def test_categorize_movement_rejects_a_reversed_movement():
    """Un movimiento revertido no cuenta como gasto."""
    from apps.budgets.exceptions import NotAnExpense
    from apps.budgets.services import categorize_movement
    from apps.ledger.services import reverse_transaction

    user = create_approved_user(email='categorizar@example.com')
    user_id = user.id
    category = CategoryFactory(user_id=user_id)
    fund_user(user_id, key='cat-8')
    movement = make_withdrawal(user_id, key='cat-8-retiro')
    reverse_transaction(transaction_id=movement.id, staff_user_id=user_id)

    with pytest.raises(NotAnExpense):
        categorize_movement(
            user_id=user_id,
            ledger_transaction_id=movement.id,
            category_id=category.id,
        )


def test_categorize_movement_rejects_an_already_categorized_movement():
    """Un movimiento no se puede categorizar dos veces."""
    from apps.budgets.exceptions import AlreadyCategorized
    from apps.budgets.services import categorize_movement

    user = create_approved_user(email='categorizar@example.com')
    user_id = user.id
    category = CategoryFactory(user_id=user_id)
    fund_user(user_id, key='cat-9')
    movement = make_withdrawal(user_id, key='cat-9-retiro')
    categorize_movement(
        user_id=user_id,
        ledger_transaction_id=movement.id,
        category_id=category.id,
    )

    with pytest.raises(AlreadyCategorized):
        categorize_movement(
            user_id=user_id,
            ledger_transaction_id=movement.id,
            category_id=category.id,
        )


def test_categorize_movement_isolates_users():
    """Dos usuarios pueden categorizar el mismo movimiento en su propia billetera."""
    from apps.budgets.exceptions import NotAnExpense
    from apps.budgets.services import categorize_movement
    from apps.ledger.services import transfer_between_users

    sender = create_approved_user(email='emisor-categorizar@example.com')
    receiver = create_approved_user(email='receptor-categorizar@example.com')
    fund_user(sender.id, key='cat-10')
    movement = transfer_between_users(
        source_user_id=sender.id,
        destination_user_id=receiver.id,
        currency='ARS',
        amount=Decimal('100.00'),
        idempotency_key='cat-10-transferencia',
        initiated_by_user_id=sender.id,
    )
    sender_category = CategoryFactory(user_id=sender.id)
    receiver_category = CategoryFactory(user_id=receiver.id)

    sender_expense = categorize_movement(
        user_id=sender.id,
        ledger_transaction_id=movement.id,
        category_id=sender_category.id,
    )

    assert sender_expense.category_id == sender_category.id
    with pytest.raises(NotAnExpense):
        categorize_movement(
            user_id=receiver.id,
            ledger_transaction_id=movement.id,
            category_id=receiver_category.id,
        )
