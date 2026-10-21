"""Tests de las tareas diarias que avisan de las cuotas de un préstamo."""

from datetime import timedelta
from decimal import Decimal

import pytest

from apps.loans.tests.factories import create_approved_user

pytestmark = pytest.mark.django_db


def create_loan(lender, borrower, key='notif'):
    """Crea un préstamo aceptado y devuelve su primera cuota."""
    from apps.ledger.services import deposit
    from apps.loans.services import accept_offer
    from apps.offers.services import create_offer

    deposit(
        user_id=lender.id,
        currency='ARS',
        amount=Decimal('10000.00'),
        idempotency_key=f'{key}-fondos',
    )
    offer = create_offer(
        lender_user_id=lender.id,
        amount=Decimal('3000.00'),
        currency='ARS',
        interest_rate=Decimal('24.00'),
        term_months=3,
    )
    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key=f'{key}-aceptar',
    )
    return loan.installments.order_by('number').first()


def test_notify_installments_due_soon_emits_the_signal():
    """La tarea avisa de las cuotas que vencen en los próximos días."""
    from apps.loans.tasks import notify_installments_due_soon

    lender = create_approved_user(email='notif-tarea-prestamista@example.com')
    borrower = create_approved_user(email='notif-tarea-prestatario@example.com')
    installment = create_loan(lender, borrower, key='notif-tarea-1')
    received = []

    from apps.loans.signals import installment_due_soon

    def receiver(sender, **kwargs):
        received.append(kwargs)

    installment_due_soon.connect(receiver)
    try:
        count = notify_installments_due_soon(today=installment.due_date - timedelta(days=1))
    finally:
        installment_due_soon.disconnect(receiver)

    assert count == 1
    assert received[0]['user_id'] == borrower.id
    assert received[0]['reference_id'] == installment.id


def test_notify_installments_due_soon_ignores_the_far_installments():
    """Una cuota que vence lejos no genera aviso."""
    from apps.loans.tasks import notify_installments_due_soon

    lender = create_approved_user(email='notif-tarea-lejos-prestamista@example.com')
    borrower = create_approved_user(email='notif-tarea-lejos-prestatario@example.com')
    installment = create_loan(lender, borrower, key='notif-tarea-2')

    count = notify_installments_due_soon(today=installment.due_date - timedelta(days=10))

    assert count == 0


def test_notify_overdue_installments_notifies_both_parties():
    """La cuota vencida avisa al prestatario y al prestamista."""
    from apps.loans.tasks import notify_overdue_installments

    lender = create_approved_user(email='notif-vencida-prestamista@example.com')
    borrower = create_approved_user(email='notif-vencida-prestatario@example.com')
    installment = create_loan(lender, borrower, key='notif-vencida')
    received = []

    from apps.loans.signals import installment_overdue

    def receiver(sender, **kwargs):
        received.append(kwargs)

    installment_overdue.connect(receiver)
    try:
        count = notify_overdue_installments(today=installment.due_date + timedelta(days=1))
    finally:
        installment_overdue.disconnect(receiver)

    assert count == 2
    notified_users = {item['user_id'] for item in received}
    assert notified_users == {borrower.id, lender.id}
    assert all(item['reference_id'] == installment.id for item in received)


def test_notify_overdue_installments_ignores_the_installments_not_due():
    """Una cuota que todavía no venció no genera aviso."""
    from apps.loans.tasks import notify_overdue_installments

    lender = create_approved_user(email='notif-no-vencida-prestamista@example.com')
    borrower = create_approved_user(email='notif-no-vencida-prestatario@example.com')
    installment = create_loan(lender, borrower, key='notif-no-vencida')

    count = notify_overdue_installments(today=installment.due_date)

    assert count == 0
