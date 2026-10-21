"""Tests de los modelos de offers."""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.offers.tests.factories import OfferFactory

pytestmark = pytest.mark.django_db


def test_offer_defaults_to_active():
    """Una oferta nueva nace activa."""
    from apps.offers.models import Offer

    offer = OfferFactory()

    assert offer.status == Offer.Status.ACTIVE
    assert offer.interest_rate == Decimal('24.00')


def test_offer_amount_must_be_positive():
    """El monto de la oferta debe ser mayor que cero."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            OfferFactory(amount=Decimal('0.00'))


def test_offer_interest_rate_must_be_positive():
    """La tasa de la oferta debe ser mayor que cero."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            OfferFactory(interest_rate=Decimal('0.00'))


def test_offer_term_months_must_be_positive():
    """El plazo de la oferta debe ser mayor que cero."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            OfferFactory(term_months=0)


def test_offer_status_choices():
    """Los estados posibles de una oferta."""
    from apps.offers.models import Offer

    assert Offer.Status.ACTIVE == 'active'
    assert Offer.Status.EXPIRED == 'expired'
    assert Offer.Status.ACCEPTED == 'accepted'


def test_offer_currency_choices():
    """Las monedas posibles de una oferta."""
    from apps.offers.models import Offer

    assert Offer.Currency.ARS == 'ARS'
    assert Offer.Currency.USD == 'USD'
