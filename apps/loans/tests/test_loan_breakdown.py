"""Tests del desglose de los movimientos que pertenecen a un préstamo."""

from datetime import date
from decimal import Decimal

import pytest

from apps.investments.tests.factories import create_approved_user as create_investor

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


def make_offer(lender_user_id, amount='3000.00', months=3):
    """Crea una oferta activa del prestamista."""
    from apps.offers.services import create_offer

    return create_offer(
        lender_user_id=lender_user_id,
        amount=Decimal(amount),
        currency='ARS',
        interest_rate=Decimal('24.00'),
        term_months=months,
    )


def create_loan(email_suffix='desglose'):
    """Crea un préstamo aceptado con su cronograma de cuotas."""
    from apps.loans.services import accept_offer
    from apps.loans.tests.factories import create_approved_user

    lender = create_approved_user(email=f'prestamista-{email_suffix}@example.com')
    borrower = create_approved_user(email=f'prestatario-{email_suffix}@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key=f'fund-{email_suffix}')

    return accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key=f'accept-{email_suffix}',
    )


def test_installment_payment_stores_its_ledger_transaction():
    """La cuota pagada guarda el id del movimiento del ledger."""
    from apps.loans.services import pay_installment

    loan = create_loan(email_suffix='pago')

    installment = pay_installment(
        loan_id=loan.id,
        number=1,
        borrower_user_id=loan.borrower_user_id,
    )

    assert installment.ledger_transaction_id is not None


def test_loan_stores_its_disbursement_transaction():
    """El préstamo guarda el id del movimiento del desembolso."""
    from apps.ledger.selectors import list_transactions_for_user

    loan = create_loan(email_suffix='desembolso')

    movements = list_transactions_for_user(user_id=loan.lender_user_id)
    disbursement = next(movement for movement in movements if movement.type == 'transfer')

    assert loan.ledger_transaction_id == disbursement.id


def test_get_loan_movement_breakdown_returns_the_installment_split():
    """El desglose de un pago de cuota devuelve capital, interés y tipo."""
    from apps.loans.selectors import get_loan_movement_breakdown
    from apps.loans.services import pay_installment

    loan = create_loan(email_suffix='split')
    installment = pay_installment(
        loan_id=loan.id,
        number=1,
        borrower_user_id=loan.borrower_user_id,
    )

    breakdown = get_loan_movement_breakdown(transaction_id=installment.ledger_transaction_id)

    assert breakdown is not None
    assert breakdown['kind'] == 'installment_payment'
    assert breakdown['interest'] == installment.interest_amount
    assert breakdown['principal'] == installment.principal_amount
    assert breakdown['currency'] == loan.currency


def test_get_loan_movement_breakdown_returns_the_disbursement():
    """El desglose de un desembolso devuelve el capital y lo marca como tal."""
    from apps.loans.selectors import get_loan_movement_breakdown

    loan = create_loan(email_suffix='desglose-desembolso')

    breakdown = get_loan_movement_breakdown(transaction_id=loan.ledger_transaction_id)

    assert breakdown is not None
    assert breakdown['kind'] == 'loan_disbursement'
    assert breakdown['principal'] == loan.principal
    assert breakdown['interest'] == Decimal('0.00')
    assert breakdown['currency'] == loan.currency


def test_get_loan_movement_breakdown_returns_none_for_other_movements():
    """Un movimiento que no es de un préstamo no tiene desglose."""
    import uuid

    from apps.ledger.services import deposit
    from apps.loans.selectors import get_loan_movement_breakdown
    from apps.loans.tests.factories import create_approved_user

    user = create_approved_user(email='ajeno-desglose@example.com')
    movement = deposit(
        user_id=user.id,
        currency='ARS',
        amount=Decimal('100.00'),
        idempotency_key='desglose-ajeno',
    )

    assert get_loan_movement_breakdown(transaction_id=movement.id) is None
    assert get_loan_movement_breakdown(transaction_id=uuid.uuid4()) is None


def test_list_loan_movement_breakdowns_resolves_a_batch():
    """El desglose por lotes devuelve el detalle de cada movimiento del préstamo."""
    from apps.loans.selectors import list_loan_movement_breakdowns
    from apps.loans.services import pay_installment

    loan = create_loan(email_suffix='lote')
    first = pay_installment(
        loan_id=loan.id,
        number=1,
        borrower_user_id=loan.borrower_user_id,
    )
    second = pay_installment(
        loan_id=loan.id,
        number=2,
        borrower_user_id=loan.borrower_user_id,
    )

    breakdowns = list_loan_movement_breakdowns(
        transaction_ids=[first.ledger_transaction_id, second.ledger_transaction_id]
    )

    assert set(breakdowns) == {first.ledger_transaction_id, second.ledger_transaction_id}
    assert all(item['kind'] == 'installment_payment' for item in breakdowns.values())
