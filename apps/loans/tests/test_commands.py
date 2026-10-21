"""Tests del management command `mark_overdue_loans`.

El command y la task de Celery llaman al mismo service (`mark_overdue`), así
que los dos caminos tienen que producir exactamente el mismo efecto.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.loans.tests.factories import create_approved_user

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


def make_offer(lender_user_id, amount='10000.00', rate='24.00', months=12, currency='ARS'):
    """Crea una oferta activa del prestamista."""
    from apps.offers.services import create_offer

    return create_offer(
        lender_user_id=lender_user_id,
        amount=Decimal(amount),
        currency=currency,
        interest_rate=Decimal(rate),
        term_months=months,
    )


def create_overdue_loan(email_suffix='command'):
    """Crea un préstamo y vencen sus cuotas para que el command tenga trabajo."""
    from apps.loans.models import Installment
    from apps.loans.services import accept_offer

    lender = create_approved_user(email=f'prestamista-{email_suffix}@example.com')
    borrower = create_approved_user(email=f'prestatario-{email_suffix}@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key=f'fund-{email_suffix}')

    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key=f'accept-{email_suffix}',
    )
    Installment.objects.filter(loan=loan).update(due_date=date.today() - timedelta(days=1))
    return loan


def test_mark_overdue_loans_command_marks_overdue_installments():
    """El command marca las cuotas vencidas y deja el préstamo en mora."""
    from apps.loans.models import Installment, Loan

    loan = create_overdue_loan(email_suffix='cmd')

    call_command('mark_overdue_loans')

    loan.refresh_from_db()
    first = loan.installments.order_by('number').first()
    assert loan.status == Loan.Status.DEFAULTED
    assert first.status == Installment.Status.OVERDUE


def test_mark_overdue_loans_command_and_the_celery_task_agree():
    """El command y la task dejan el préstamo en el mismo estado."""
    from apps.loans.models import Installment, Loan

    loan_from_command = create_overdue_loan(email_suffix='cmd-igual')
    call_command('mark_overdue_loans')

    loan_from_task = create_overdue_loan(email_suffix='task-igual')

    from apps.loans.tasks import mark_overdue_loans

    marked = mark_overdue_loans(today=date.today())

    for loan in (loan_from_command, loan_from_task):
        loan.refresh_from_db()
        assert loan.status == Loan.Status.DEFAULTED
        assert loan.installments.filter(status=Installment.Status.OVERDUE).count() == 12
    assert marked == 12
