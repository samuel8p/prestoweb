"""Tests de los servicios de escritura de offers."""

import uuid
from decimal import Decimal

import pytest

from apps.offers.tests.factories import OfferFactory, create_approved_user

pytestmark = pytest.mark.django_db


def test_create_offer_creates_active_offer():
    """Crear una oferta deja una oferta activa del prestamista."""
    from apps.offers.models import Offer
    from apps.offers.services import create_offer

    user = create_approved_user()

    offer = create_offer(
        lender_user_id=user.id,
        amount=Decimal('10000.00'),
        currency=Offer.Currency.ARS,
        interest_rate=Decimal('24.00'),
        term_months=12,
        requirements='Sin requisitos',
    )

    assert offer.status == Offer.Status.ACTIVE
    assert offer.lender_user_id == user.id
    assert offer.amount == Decimal('10000.00')


def test_create_offer_requires_approved_kyc():
    """Sin KYC aprobada no se puede publicar una oferta."""
    from apps.core.exceptions import KYCNotCompleted
    from apps.identity.services import register_user
    from apps.offers.models import Offer
    from apps.offers.services import create_offer

    user = register_user(email='sin-kyc@example.com', password='TestPass123!')

    with pytest.raises(KYCNotCompleted):
        create_offer(
            lender_user_id=user.id,
            amount=Decimal('10000.00'),
            currency=Offer.Currency.ARS,
            interest_rate=Decimal('24.00'),
            term_months=12,
        )


def test_create_offer_does_not_reserve_funds():
    """Publicar una oferta no mueve dinero ni crea asientos."""
    from apps.ledger.models import Account, LedgerTransaction
    from apps.offers.models import Offer
    from apps.offers.services import create_offer

    user = create_approved_user()
    accounts_before = Account.objects.count()
    transactions_before = LedgerTransaction.objects.count()

    create_offer(
        lender_user_id=user.id,
        amount=Decimal('10000.00'),
        currency=Offer.Currency.ARS,
        interest_rate=Decimal('24.00'),
        term_months=12,
    )

    assert Account.objects.count() == accounts_before
    assert LedgerTransaction.objects.count() == transactions_before


def test_create_offer_rejects_invalid_amount():
    """Un monto no positivo se rechaza."""
    from apps.core.exceptions import InvalidAmount
    from apps.offers.models import Offer
    from apps.offers.services import create_offer

    user = create_approved_user()

    with pytest.raises(InvalidAmount):
        create_offer(
            lender_user_id=user.id,
            amount=Decimal('0.00'),
            currency=Offer.Currency.ARS,
            interest_rate=Decimal('24.00'),
            term_months=12,
        )


def test_update_offer_changes_fields():
    """El prestamista puede actualizar los datos de su oferta activa."""
    from apps.offers.services import update_offer

    user = create_approved_user()
    offer = OfferFactory(lender_user_id=user.id, amount=Decimal('5000.00'))

    updated = update_offer(
        offer_id=offer.id,
        lender_user_id=user.id,
        amount=Decimal('8000.00'),
    )

    assert updated.amount == Decimal('8000.00')


def test_update_offer_rejects_other_lender():
    """No se puede actualizar la oferta de otro prestamista."""
    from apps.offers.exceptions import OfferNotFound
    from apps.offers.services import update_offer

    user = create_approved_user()
    other = create_approved_user(email='otro-prestamista@example.com')
    offer = OfferFactory(lender_user_id=other.id)

    with pytest.raises(OfferNotFound):
        update_offer(
            offer_id=offer.id,
            lender_user_id=user.id,
            amount=Decimal('8000.00'),
        )


def test_update_offer_rejects_expired_offer():
    """Una oferta expirada no se puede modificar."""
    from apps.offers.exceptions import OfferNotEditable
    from apps.offers.models import Offer
    from apps.offers.services import update_offer

    user = create_approved_user()
    offer = OfferFactory(lender_user_id=user.id, status=Offer.Status.EXPIRED)

    with pytest.raises(OfferNotEditable):
        update_offer(
            offer_id=offer.id,
            lender_user_id=user.id,
            amount=Decimal('8000.00'),
        )


def test_expire_offer_sets_status():
    """El prestamista puede expirar su propia oferta."""
    from apps.offers.models import Offer
    from apps.offers.services import expire_offer

    user = create_approved_user()
    offer = OfferFactory(lender_user_id=user.id)

    expired = expire_offer(offer_id=offer.id, lender_user_id=user.id)

    assert expired.status == Offer.Status.EXPIRED


def test_accept_offer_marks_offer_as_accepted():
    """Aceptar una oferta la marca como aceptada."""
    from apps.offers.models import Offer
    from apps.offers.services import accept_offer

    user = create_approved_user()
    offer = OfferFactory(lender_user_id=uuid.uuid4())

    accepted = accept_offer(offer_id=offer.id, borrower_user_id=user.id)

    assert accepted.status == Offer.Status.ACCEPTED


def test_accept_offer_rejects_unknown_offer():
    """Una oferta inexistente no se puede aceptar."""
    from apps.offers.exceptions import OfferNotFound
    from apps.offers.services import accept_offer

    user = create_approved_user()

    with pytest.raises(OfferNotFound):
        accept_offer(offer_id=uuid.uuid4(), borrower_user_id=user.id)


def test_accept_offer_rejects_inactive_offer():
    """Una oferta que no está activa no se puede aceptar."""
    from apps.offers.exceptions import OfferNotAcceptable
    from apps.offers.models import Offer
    from apps.offers.services import accept_offer

    user = create_approved_user()
    offer = OfferFactory(lender_user_id=uuid.uuid4(), status=Offer.Status.EXPIRED)

    with pytest.raises(OfferNotAcceptable):
        accept_offer(offer_id=offer.id, borrower_user_id=user.id)


def test_accept_offer_rejects_own_offer():
    """El prestamista no puede aceptar su propia oferta."""
    from apps.offers.exceptions import CannotAcceptOwnOffer
    from apps.offers.services import accept_offer

    user = create_approved_user()
    offer = OfferFactory(lender_user_id=user.id)

    with pytest.raises(CannotAcceptOwnOffer):
        accept_offer(offer_id=offer.id, borrower_user_id=user.id)
