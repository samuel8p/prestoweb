"""Tests de los modelos de loans."""

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.loans.tests.factories import (
    InstallmentFactory,
    LoanFactory,
    OfferTermsSnapshotFactory,
)

pytestmark = pytest.mark.django_db


def test_loan_defaults_to_active():
    """Un préstamo nace activo."""
    from apps.loans.models import Loan

    loan = LoanFactory()

    assert loan.status == Loan.Status.ACTIVE
    assert loan.principal == Decimal('10000.00')


def test_loan_status_choices_have_no_pending():
    """Los estados del préstamo no incluyen pending."""
    from apps.loans.models import Loan

    statuses = {status for status, _ in Loan.Status.choices}

    assert statuses == {'active', 'paid', 'defaulted'}
    assert 'pending' not in statuses


def test_loan_idempotency_key_is_unique_per_borrower():
    """La clave de idempotencia es única por prestatario."""
    import uuid

    from apps.loans.models import Loan

    borrower_id = uuid.uuid4()
    LoanFactory(borrower_user_id=borrower_id, idempotency_key='k1')

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LoanFactory(borrower_user_id=borrower_id, idempotency_key='k1')


def test_loan_idempotency_key_can_repeat_for_another_borrower():
    """Dos prestatarios distintos pueden usar la misma clave."""
    import uuid

    from apps.loans.models import Loan

    LoanFactory(borrower_user_id=uuid.uuid4(), idempotency_key='k1')
    LoanFactory(borrower_user_id=uuid.uuid4(), idempotency_key='k1')

    assert Loan.objects.filter(idempotency_key='k1').count() == 2


def test_loan_principal_must_be_positive():
    """El principal del préstamo debe ser mayor que cero."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LoanFactory(principal=Decimal('0.00'))


def test_loan_term_months_must_be_positive():
    """El plazo del préstamo debe ser mayor que cero."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LoanFactory(term_months=0)


def test_offer_terms_snapshot_is_one_to_one_with_loan():
    """Cada préstamo tiene un único snapshot de términos."""
    from apps.loans.models import OfferTermsSnapshot

    loan = LoanFactory()
    OfferTermsSnapshotFactory(loan=loan)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            OfferTermsSnapshotFactory(loan=loan)


def test_offer_terms_snapshot_is_immutable_by_default():
    """El snapshot de términos es inmutable por defecto."""
    snapshot = OfferTermsSnapshotFactory()

    assert snapshot.is_immutable is True


def test_installment_number_is_unique_per_loan():
    """El número de cuota es único dentro del préstamo."""
    from apps.loans.models import Installment

    loan = LoanFactory()
    InstallmentFactory(loan=loan, number=1)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            InstallmentFactory(loan=loan, number=1)


def test_installment_principal_must_be_positive():
    """La parte de capital de la cuota debe ser mayor que cero."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            InstallmentFactory(principal_amount=Decimal('0.00'))


def test_installment_interest_must_be_non_negative():
    """La parte de interés de la cuota no puede ser negativa."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            InstallmentFactory(interest_amount=Decimal('-1.00'))


def test_installment_status_choices():
    """Los estados posibles de una cuota."""
    from apps.loans.models import Installment

    assert Installment.Status.PENDING == 'pending'
    assert Installment.Status.PAID == 'paid'
    assert Installment.Status.OVERDUE == 'overdue'


def test_installments_are_ordered_by_number():
    """Las cuotas de un préstamo se ordenan por número."""
    from apps.loans.models import Installment

    loan = LoanFactory()
    InstallmentFactory(loan=loan, number=2, due_date=date(2026, 2, 28))
    InstallmentFactory(loan=loan, number=1, due_date=date(2026, 1, 31))

    numbers = list(
        Installment.objects.filter(loan=loan).order_by('number').values_list('number', flat=True)
    )

    assert numbers == [1, 2]
