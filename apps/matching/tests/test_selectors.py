"""Tests de los selectores de matching (app de solo lectura)."""

from decimal import Decimal

import pytest

from apps.offers.tests.factories import OfferFactory

pytestmark = pytest.mark.django_db


def test_search_offers_returns_active_offers():
    """La búsqueda devuelve las ofertas activas."""
    from apps.matching.selectors import search_offers

    OfferFactory()
    OfferFactory()

    results = search_offers()

    assert len(results) == 2
    assert all('amount' in result for result in results)


def test_search_offers_excludes_non_active_offers():
    """La búsqueda ignora las ofertas que no están activas."""
    from apps.matching.selectors import search_offers

    OfferFactory(status='active')
    OfferFactory(status='expired')

    assert len(search_offers()) == 1


def test_search_offers_applies_filters():
    """La búsqueda aplica los filtros indicados."""
    from apps.matching.selectors import search_offers

    OfferFactory(currency='ARS', amount=Decimal('5000.00'))
    OfferFactory(currency='USD', amount=Decimal('20000.00'))

    results = search_offers(currency='USD', amount_min=Decimal('10000.00'))

    assert len(results) == 1
    assert results[0]['currency'] == 'USD'
    assert results[0]['amount'] == Decimal('20000.00')


def test_search_offers_filters_by_maximum_amount():
    """La búsqueda filtra por monto máximo."""
    from apps.matching.selectors import search_offers

    OfferFactory(amount=Decimal('5000.00'))
    OfferFactory(amount=Decimal('20000.00'))

    results = search_offers(amount_max=Decimal('10000.00'))

    assert len(results) == 1
    assert results[0]['amount'] == Decimal('5000.00')


def test_search_offers_filters_by_amount_range():
    """La búsqueda filtra por rango de montos."""
    from apps.matching.selectors import search_offers

    OfferFactory(amount=Decimal('5000.00'))
    OfferFactory(amount=Decimal('15000.00'))
    OfferFactory(amount=Decimal('50000.00'))

    results = search_offers(amount_min=Decimal('10000.00'), amount_max=Decimal('20000.00'))

    assert len(results) == 1
    assert results[0]['amount'] == Decimal('15000.00')


def test_search_offers_orders_by_rate():
    """La búsqueda ordena por tasa, luego plazo y luego monto."""
    from apps.matching.selectors import search_offers

    OfferFactory(interest_rate=Decimal('30.00'), amount=Decimal('1000.00'))
    OfferFactory(interest_rate=Decimal('15.00'), amount=Decimal('2000.00'))

    results = search_offers()

    assert [result['interest_rate'] for result in results] == [
        Decimal('15.00'),
        Decimal('30.00'),
    ]


def test_compare_offers_returns_installment_interest_and_cost():
    """La comparación devuelve cuota, interés total y costo total."""
    from apps.matching.selectors import compare_offers

    first = OfferFactory(
        amount=Decimal('10000.00'),
        interest_rate=Decimal('24.00'),
        term_months=12,
    )
    second = OfferFactory(
        amount=Decimal('20000.00'),
        interest_rate=Decimal('12.00'),
        term_months=24,
    )

    results = compare_offers(offer_ids=[first.id, second.id])

    assert len(results) == 2
    compared = next(result for result in results if result['id'] == first.id)
    assert compared['installment'] == Decimal('945.60')
    assert compared['total_interest'] == Decimal('1347.20')
    assert compared['total_cost'] == Decimal('11347.20')


def test_compare_offers_requires_at_least_two_offers():
    """Comparar una sola oferta no tiene sentido."""
    from apps.matching.exceptions import NotEnoughOffersToCompare
    from apps.matching.selectors import compare_offers

    offer = OfferFactory()

    with pytest.raises(NotEnoughOffersToCompare):
        compare_offers(offer_ids=[offer.id])


def test_compare_offers_rejects_unknown_offer():
    """Una oferta inexistente no se puede comparar."""
    import uuid

    from apps.matching.exceptions import OfferNotFound
    from apps.matching.selectors import compare_offers

    offer = OfferFactory()

    with pytest.raises(OfferNotFound):
        compare_offers(offer_ids=[offer.id, uuid.uuid4()])


def test_compare_offers_rejects_inactive_offer():
    """Una oferta que no está activa no se puede comparar."""
    from apps.matching.exceptions import OfferNotFound
    from apps.matching.selectors import compare_offers

    active = OfferFactory(status='active')
    expired = OfferFactory(status='expired')

    with pytest.raises(OfferNotFound):
        compare_offers(offer_ids=[active.id, expired.id])


def test_compare_offers_values_match_core_money():
    """La comparación usa los cálculos de core/money.py."""
    from apps.core.money import french_installment
    from apps.matching.selectors import compare_offers

    first = OfferFactory(
        amount=Decimal('50000.00'),
        interest_rate=Decimal('18.00'),
        term_months=18,
    )
    second = OfferFactory(
        amount=Decimal('30000.00'),
        interest_rate=Decimal('30.00'),
        term_months=6,
    )

    results = compare_offers(offer_ids=[first.id, second.id])

    for result in results:
        expected = french_installment(
            principal=result['amount'],
            annual_tna=result['interest_rate'],
            months=result['term_months'],
        )
        assert result['installment'] == expected
        assert result['total_cost'] == expected * result['term_months']
