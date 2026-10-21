import uuid
from datetime import date
from decimal import Decimal

import factory

from apps.loans.models import Installment, Loan, OfferTermsSnapshot


class LoanFactory(factory.django.DjangoModelFactory):
    """Factory de Loan."""

    class Meta:
        model = Loan

    borrower_user_id = factory.LazyFunction(uuid.uuid4)
    lender_user_id = factory.LazyFunction(uuid.uuid4)
    offer_id = factory.LazyFunction(uuid.uuid4)
    principal = Decimal('10000.00')
    currency = 'ARS'
    interest_rate = Decimal('24.00')
    term_months = 12
    status = Loan.Status.ACTIVE
    idempotency_key = factory.Sequence(lambda n: f'loan-key-{n}')
    request_hash = factory.Sequence(lambda n: f'loan-hash-{n}')


class OfferTermsSnapshotFactory(factory.django.DjangoModelFactory):
    """Factory de OfferTermsSnapshot."""

    class Meta:
        model = OfferTermsSnapshot

    loan = factory.SubFactory(LoanFactory)
    accepted_by_user_id = factory.LazyFunction(uuid.uuid4)
    snapshot_data = factory.LazyAttribute(lambda _: {'amount': '10000.00'})
    is_immutable = True


class InstallmentFactory(factory.django.DjangoModelFactory):
    """Factory de Installment."""

    class Meta:
        model = Installment

    loan = factory.SubFactory(LoanFactory)
    number = 1
    due_date = date(2026, 1, 31)
    principal_amount = Decimal('800.00')
    interest_amount = Decimal('145.60')
    amount = Decimal('945.60')
    status = Installment.Status.PENDING


def create_approved_user(email: str = 'prestatario@example.com'):
    """Crea un usuario con KYC aprobada usando los servicios de identity."""
    from apps.identity.services import register_user, resolve_kyc, submit_kyc

    user = register_user(email=email, password='TestPass123!')
    verification = submit_kyc(user=user, documents={})
    resolve_kyc(
        verification_id=verification.id,
        status='approved',
        resolved_by_user_id=uuid.uuid4(),
    )
    return user
