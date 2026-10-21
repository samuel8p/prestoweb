"""Tests de los selectores de lectura de offers."""

from decimal import Decimal

import pytest

from apps.offers.tests.factories import OfferFactory, create_approved_user

pytestmark = pytest.mark.django_db


def test_get_offer_returns_own_offer():
    """El selector devuelve la oferta del propio prestamista."""
    from apps.offers.selectors import get_offer

    user = create_approved_user()
    offer = OfferFactory(lender_user_id=user.id)

    found = get_offer(offer_id=offer.id, lender_user_id=user.id)

    assert found is not None
    assert found.id == offer.id


def test_get_offer_returns_none_for_other_lender():
    """El selector no expone ofertas de otros prestamistas."""
    from apps.offers.selectors import get_offer

    user = create_approved_user()
    other = create_approved_user(email='prestamista-ajeno@example.com')
    offer = OfferFactory(lender_user_id=other.id)

    assert get_offer(offer_id=offer.id, lender_user_id=user.id) is None


def test_list_offers_for_lender_only_own():
    """El listado devuelve solo las ofertas del prestamista."""
    from apps.offers.selectors import list_offers_for_lender

    user = create_approved_user()
    other = create_approved_user(email='listado-prestamista@example.com')
    OfferFactory(lender_user_id=user.id)
    OfferFactory(lender_user_id=other.id)

    offers = list_offers_for_lender(lender_user_id=user.id)

    assert [offer.lender_user_id for offer in offers] == [user.id]


def test_search_active_offers_filters_by_currency():
    """La búsqueda filtra por moneda."""
    from apps.offers.models import Offer
    from apps.offers.selectors import search_active_offers

    OfferFactory(currency=Offer.Currency.ARS)
    OfferFactory(currency=Offer.Currency.USD)

    offers = search_active_offers(currency=Offer.Currency.USD)

    assert [offer.currency for offer in offers] == [Offer.Currency.USD]


def test_search_active_offers_filters_by_minimum_amount():
    """La búsqueda filtra por monto mínimo."""
    from apps.offers.selectors import search_active_offers

    OfferFactory(amount=Decimal('5000.00'))
    OfferFactory(amount=Decimal('20000.00'))

    offers = search_active_offers(amount_min=Decimal('10000.00'))

    assert [offer.amount for offer in offers] == [Decimal('20000.00')]


def test_search_active_offers_filters_by_maximum_amount():
    """La búsqueda filtra por monto máximo."""
    from apps.offers.selectors import search_active_offers

    OfferFactory(amount=Decimal('5000.00'))
    OfferFactory(amount=Decimal('20000.00'))

    offers = search_active_offers(amount_max=Decimal('10000.00'))

    assert [offer.amount for offer in offers] == [Decimal('5000.00')]


def test_search_active_offers_filters_by_amount_range():
    """La búsqueda filtra por rango de montos."""
    from apps.offers.selectors import search_active_offers

    OfferFactory(amount=Decimal('5000.00'))
    OfferFactory(amount=Decimal('15000.00'))
    OfferFactory(amount=Decimal('50000.00'))

    offers = search_active_offers(amount_min=Decimal('10000.00'), amount_max=Decimal('20000.00'))

    assert [offer.amount for offer in offers] == [Decimal('15000.00')]


def test_search_active_offers_filters_by_max_rate():
    """La búsqueda filtra por tasa máxima."""
    from apps.offers.selectors import search_active_offers

    OfferFactory(interest_rate=Decimal('15.00'))
    OfferFactory(interest_rate=Decimal('30.00'))

    offers = search_active_offers(max_rate=Decimal('20.00'))

    assert [offer.interest_rate for offer in offers] == [Decimal('15.00')]


def test_search_active_offers_filters_by_term_months():
    """La búsqueda filtra por plazo."""
    from apps.offers.selectors import search_active_offers

    OfferFactory(term_months=6)
    OfferFactory(term_months=12)

    offers = search_active_offers(term_months=12)

    assert [offer.term_months for offer in offers] == [12]


def test_search_active_offers_excludes_non_active():
    """La búsqueda solo devuelve ofertas activas."""
    from apps.offers.models import Offer
    from apps.offers.selectors import search_active_offers

    OfferFactory(status=Offer.Status.ACTIVE)
    OfferFactory(status=Offer.Status.EXPIRED)
    OfferFactory(status=Offer.Status.ACCEPTED)

    offers = search_active_offers()

    assert [offer.status for offer in offers] == [Offer.Status.ACTIVE]


def test_search_active_offers_orders_by_rate():
    """La búsqueda ordena por tasa, luego plazo y luego monto."""
    from apps.offers.selectors import search_active_offers

    OfferFactory(interest_rate=Decimal('30.00'), amount=Decimal('1000.00'))
    OfferFactory(interest_rate=Decimal('15.00'), amount=Decimal('2000.00'))
    OfferFactory(interest_rate=Decimal('15.00'), amount=Decimal('3000.00'))

    offers = search_active_offers()

    assert [offer.interest_rate for offer in offers] == [
        Decimal('15.00'),
        Decimal('15.00'),
        Decimal('30.00'),
    ]
    assert [offer.amount for offer in offers] == [
        Decimal('2000.00'),
        Decimal('3000.00'),
        Decimal('1000.00'),
    ]


def test_search_active_offers_orders_by_term_and_amount():
    """La búsqueda también admite ordenar por plazo y por monto."""
    from apps.offers.selectors import search_active_offers

    OfferFactory(term_months=12, amount=Decimal('1000.00'))
    OfferFactory(term_months=6, amount=Decimal('2000.00'))
    OfferFactory(amount=Decimal('5000.00'), term_months=6)

    by_term = search_active_offers(ordering='term')
    by_amount = search_active_offers(ordering='amount')

    assert [offer.term_months for offer in by_term] == [6, 6, 12]
    assert [offer.amount for offer in by_amount] == [
        Decimal('1000.00'),
        Decimal('2000.00'),
        Decimal('5000.00'),
    ]


def test_get_active_offer_returns_only_active_offers():
    """El selector de detalle para matching solo devuelve ofertas activas."""
    from apps.offers.models import Offer
    from apps.offers.selectors import get_active_offer

    active = OfferFactory(status=Offer.Status.ACTIVE)
    expired = OfferFactory(status=Offer.Status.EXPIRED)

    assert get_active_offer(offer_id=active.id) is not None
    assert get_active_offer(offer_id=expired.id) is None
