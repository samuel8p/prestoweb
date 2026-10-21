"""Tests de la API de matching."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.offers.tests.factories import OfferFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def authenticate(client, user):
    """Autentica al cliente con un access token del usuario dado."""
    from rest_framework_simplejwt.tokens import RefreshToken

    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


def test_matching_offers_requires_authentication(client):
    """La búsqueda exige autenticación."""
    response = client.get('/api/v1/matching/offers/')

    assert response.status_code == 401
    assert response.data['error']['code'] == 'not_authenticated'


def test_matching_offers_returns_active_offers(client):
    """La búsqueda devuelve las ofertas activas del marketplace."""
    from apps.offers.tests.factories import create_approved_user

    user = create_approved_user()
    OfferFactory()
    OfferFactory(status='expired')
    authenticate(client, user)

    response = client.get('/api/v1/matching/offers/')

    assert response.status_code == 200
    assert len(response.data['results']) == 1


def test_matching_offers_applies_filters(client):
    """La búsqueda aplica los filtros de la query string."""
    from apps.offers.tests.factories import create_approved_user

    user = create_approved_user()
    OfferFactory(currency='ARS', amount=Decimal('5000.00'), interest_rate=Decimal('30.00'))
    OfferFactory(currency='USD', amount=Decimal('20000.00'), interest_rate=Decimal('10.00'))
    authenticate(client, user)

    response = client.get(
        '/api/v1/matching/offers/',
        {
            'currency': 'USD',
            'amount_min': '10000.00',
            'amount_max': '30000.00',
            'max_rate': '15.00',
        },
    )

    assert response.status_code == 200
    assert len(response.data['results']) == 1
    assert response.data['results'][0]['currency'] == 'USD'


def test_matching_offers_filters_by_maximum_amount(client):
    """La búsqueda filtra por monto máximo."""
    from apps.offers.tests.factories import create_approved_user

    user = create_approved_user()
    OfferFactory(amount=Decimal('5000.00'))
    OfferFactory(amount=Decimal('20000.00'))
    authenticate(client, user)

    response = client.get('/api/v1/matching/offers/', {'amount_max': '10000.00'})

    assert response.status_code == 200
    assert len(response.data['results']) == 1
    assert response.data['results'][0]['amount'] == '5000.00'


def test_matching_offers_rejects_invalid_currency(client):
    """Una moneda inválida devuelve 400."""
    from apps.offers.tests.factories import create_approved_user

    user = create_approved_user()
    authenticate(client, user)

    response = client.get('/api/v1/matching/offers/', {'currency': 'EUR'})

    assert response.status_code == 400


def test_matching_offers_orders_by_rate(client):
    """La búsqueda ordena por tasa."""
    from apps.offers.tests.factories import create_approved_user

    user = create_approved_user()
    OfferFactory(interest_rate=Decimal('30.00'))
    OfferFactory(interest_rate=Decimal('15.00'))
    authenticate(client, user)

    response = client.get('/api/v1/matching/offers/')

    rates = [result['interest_rate'] for result in response.data['results']]
    assert rates == ['15.00', '30.00']


def test_matching_offers_are_paginated(client):
    """La búsqueda pagina los resultados."""
    from apps.offers.tests.factories import create_approved_user

    user = create_approved_user()
    for _ in range(3):
        OfferFactory()
    authenticate(client, user)

    response = client.get('/api/v1/matching/offers/', {'page_size': 2})

    assert response.status_code == 200
    assert len(response.data['results']) == 2
    assert response.data['count'] == 3
    assert 'next' in response.data


def test_matching_comparison_requires_authentication(client):
    """La comparación exige autenticación."""
    response = client.post('/api/v1/matching/comparisons/', {'offer_ids': []}, format='json')

    assert response.status_code == 401


def test_matching_comparison_returns_installment_interest_and_cost(client):
    """La comparación devuelve cuota, interés total y costo total."""
    from apps.offers.tests.factories import create_approved_user

    user = create_approved_user()
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
    authenticate(client, user)

    response = client.post(
        '/api/v1/matching/comparisons/',
        {'offer_ids': [str(first.id), str(second.id)]},
        format='json',
    )

    assert response.status_code == 200
    assert len(response.data) == 2
    compared = next(item for item in response.data if item['id'] == str(first.id))
    assert compared['installment'] == '945.60'
    assert compared['total_interest'] == '1347.20'
    assert compared['total_cost'] == '11347.20'


def test_matching_comparison_requires_two_offers(client):
    """Comparar una sola oferta devuelve 400."""
    from apps.offers.tests.factories import create_approved_user

    user = create_approved_user()
    offer = OfferFactory()
    authenticate(client, user)

    response = client.post(
        '/api/v1/matching/comparisons/',
        {'offer_ids': [str(offer.id)]},
        format='json',
    )

    assert response.status_code == 400


def test_matching_comparison_rejects_unknown_offer(client):
    """Una oferta inexistente devuelve 404."""
    import uuid

    from apps.offers.tests.factories import create_approved_user

    user = create_approved_user()
    offer = OfferFactory()
    authenticate(client, user)

    response = client.post(
        '/api/v1/matching/comparisons/',
        {'offer_ids': [str(offer.id), str(uuid.uuid4())]},
        format='json',
    )

    assert response.status_code == 404
    assert response.data['error']['code'] == 'not_found'


def test_matching_comparison_rejects_expired_offer(client):
    """Una oferta expirada devuelve 404."""
    from apps.offers.tests.factories import create_approved_user

    user = create_approved_user()
    active = OfferFactory(status='active')
    expired = OfferFactory(status='expired')
    authenticate(client, user)

    response = client.post(
        '/api/v1/matching/comparisons/',
        {'offer_ids': [str(active.id), str(expired.id)]},
        format='json',
    )

    assert response.status_code == 404


def test_matching_comparison_rejects_missing_offer_ids(client):
    """Sin offer_ids la comparación devuelve 400."""
    from apps.offers.tests.factories import create_approved_user

    user = create_approved_user()
    authenticate(client, user)

    response = client.post('/api/v1/matching/comparisons/', {}, format='json')

    assert response.status_code == 400


def test_matching_does_not_expose_inactive_offers(client):
    """El marketplace solo muestra ofertas activas."""
    from apps.offers.tests.factories import create_approved_user

    user = create_approved_user()
    OfferFactory(status='accepted')
    authenticate(client, user)

    response = client.get('/api/v1/matching/offers/')

    assert response.status_code == 200
    assert response.data['count'] == 0
