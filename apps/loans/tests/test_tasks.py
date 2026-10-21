"""Tests de las tareas Celery de loans.

La tarea es un adaptador delgado sobre `services.mark_overdue`: la regla de
negocio vive en el service y la task solo la dispara (AGENTS §5.1).
"""

from datetime import date
from decimal import Decimal

import pytest

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


def create_loan_with_installments(email_suffix='task'):
    """Crea un préstamo aceptado con su cronograma de cuotas."""
    from apps.loans.services import accept_offer

    lender = create_approved_user(email=f'prestamista-{email_suffix}@example.com')
    borrower = create_approved_user(email=f'prestatario-{email_suffix}@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key=f'fund-{email_suffix}')

    return accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key=f'accept-{email_suffix}',
    )


def test_mark_overdue_loans_task_is_registered_with_its_name():
    """La task se registra con el nombre que usa el beat schedule."""
    from apps.loans.tasks import mark_overdue_loans

    assert mark_overdue_loans.name == 'apps.loans.tasks.mark_overdue_loans'


def test_mark_overdue_loans_task_is_discovered_by_the_celery_app():
    """El descubrimiento automático registra la task de la app de loans."""
    from config.celery import app

    assert 'apps.loans.tasks.mark_overdue_loans' in app.tasks


def test_mark_overdue_loans_task_marks_overdue_installments():
    """La task marca las cuotas vencidas y deja el préstamo en mora."""
    from apps.loans.models import Installment, Loan
    from apps.loans.tasks import mark_overdue_loans

    loan = create_loan_with_installments(email_suffix='vencida')

    marked = mark_overdue_loans(today=date(2030, 1, 1))

    loan.refresh_from_db()
    first = loan.installments.order_by('number').first()
    assert marked == 12
    assert loan.status == Loan.Status.DEFAULTED
    assert first.status == Installment.Status.OVERDUE


def test_mark_overdue_loans_task_is_idempotent():
    """Correr la task dos veces no vuelve a marcar las mismas cuotas."""
    from apps.loans.models import Installment
    from apps.loans.tasks import mark_overdue_loans

    loan = create_loan_with_installments(email_suffix='idem')

    first = mark_overdue_loans(today=date(2030, 1, 1))
    second = mark_overdue_loans(today=date(2030, 1, 1))

    loan.refresh_from_db()
    overdue = loan.installments.filter(status=Installment.Status.OVERDUE).count()
    assert first == 12
    assert second == 0
    assert overdue == 12


def test_mark_overdue_loans_task_ignores_installments_not_due():
    """Una cuota que no venció no se marca."""
    from apps.loans.models import Installment, Loan
    from apps.loans.tasks import mark_overdue_loans

    loan = create_loan_with_installments(email_suffix='futura')

    marked = mark_overdue_loans(today=date(2020, 1, 1))

    loan.refresh_from_db()
    assert marked == 0
    assert loan.status == Loan.Status.ACTIVE
    assert loan.installments.filter(status=Installment.Status.PENDING).count() == 12


def test_mark_overdue_loans_task_runs_as_a_celery_task():
    """La task se puede ejecutar como tarea Celery (`.apply()`), no solo como función."""
    from apps.loans.tasks import mark_overdue_loans

    create_loan_with_installments(email_suffix='apply')

    result = mark_overdue_loans.apply(kwargs={'today': date(2030, 1, 1)})

    assert result.successful()
    assert result.get() == 12
