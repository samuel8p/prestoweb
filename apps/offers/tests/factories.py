import uuid
from decimal import Decimal

import factory

from apps.offers.models import Offer


class OfferFactory(factory.django.DjangoModelFactory):
    """Factory de Offer."""

    class Meta:
        model = Offer

    lender_user_id = factory.LazyFunction(uuid.uuid4)
    amount = Decimal('10000.00')
    currency = Offer.Currency.ARS
    interest_rate = Decimal('24.00')
    term_months = 12
    requirements = 'Sin requisitos'
    status = Offer.Status.ACTIVE


def create_approved_user(email: str = 'prestamista@example.com'):
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
