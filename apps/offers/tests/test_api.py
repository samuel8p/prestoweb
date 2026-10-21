"""Tests de la API de offers."""

import pytest
from rest_framework.test import APIClient

from apps.offers.tests.factories import OfferFactory, create_approved_user

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


def test_offers_list_requires_authentication(client):
    """El listado de ofertas exige autenticación."""
    response = client.get('/api/v1/offers/')

    assert response.status_code == 401
    assert response.data['error']['code'] == 'not_authenticated'


def test_offers_list_returns_only_own_offers(client):
    """El listado devuelve solo las ofertas del prestamista."""
    user = create_approved_user()
    other = create_approved_user(email='otro-ofertas@example.com')
    OfferFactory(lender_user_id=user.id)
    OfferFactory(lender_user_id=other.id)
    authenticate(client, user)

    response = client.get('/api/v1/offers/')

    assert response.status_code == 200
    assert [offer['lender_user_id'] for offer in response.data['results']] == [str(user.id)]


def test_create_offer_returns_201(client):
    """Publicar una oferta devuelve 201."""
    user = create_approved_user()
    authenticate(client, user)

    response = client.post(
        '/api/v1/offers/',
        {
            'amount': '10000.00',
            'currency': 'ARS',
            'interest_rate': '24.00',
            'term_months': 12,
            'requirements': 'Sin requisitos',
        },
        format='json',
    )

    assert response.status_code == 201
    assert response.data['status'] == 'active'
    assert response.data['interest_rate'] == '24.00'


def test_create_offer_requires_approved_kyc(client):
    """Sin KYC aprobada publicar una oferta devuelve 403."""
    from apps.identity.services import register_user

    user = register_user(email='ofertas-sin-kyc@example.com', password='TestPass123!')
    authenticate(client, user)

    response = client.post(
        '/api/v1/offers/',
        {
            'amount': '10000.00',
            'currency': 'ARS',
            'interest_rate': '24.00',
            'term_months': 12,
        },
        format='json',
    )

    assert response.status_code == 403


def test_create_offer_rejects_invalid_amount(client):
    """Un monto no positivo devuelve 400."""
    user = create_approved_user()
    authenticate(client, user)

    response = client.post(
        '/api/v1/offers/',
        {
            'amount': '0.00',
            'currency': 'ARS',
            'interest_rate': '24.00',
            'term_months': 12,
        },
        format='json',
    )

    assert response.status_code == 400
    assert response.data['error']['code'] == 'validation_error'


def test_offer_detail_of_other_lender_returns_404(client):
    """No se puede ver la oferta de otro prestamista."""
    user = create_approved_user()
    other = create_approved_user(email='detalle-oferta@example.com')
    offer = OfferFactory(lender_user_id=other.id)
    authenticate(client, user)

    response = client.get(f'/api/v1/offers/{offer.id}/')

    assert response.status_code == 404
    assert response.data['error']['code'] == 'not_found'


def test_offer_detail_of_own_offer_returns_200(client):
    """El prestamista ve su propia oferta."""
    user = create_approved_user()
    offer = OfferFactory(lender_user_id=user.id)
    authenticate(client, user)

    response = client.get(f'/api/v1/offers/{offer.id}/')

    assert response.status_code == 200
    assert response.data['id'] == str(offer.id)


def test_patch_own_offer_updates_amount(client):
    """El prestamista puede actualizar su oferta."""
    user = create_approved_user()
    offer = OfferFactory(lender_user_id=user.id, amount='5000.00')
    authenticate(client, user)

    response = client.patch(
        f'/api/v1/offers/{offer.id}/',
        {'amount': '8000.00'},
        format='json',
    )

    assert response.status_code == 200
    assert response.data['amount'] == '8000.00'


def test_patch_other_lender_offer_returns_404(client):
    """No se puede actualizar la oferta de otro prestamista."""
    user = create_approved_user()
    other = create_approved_user(email='patch-ajeno@example.com')
    offer = OfferFactory(lender_user_id=other.id)
    authenticate(client, user)

    response = client.patch(
        f'/api/v1/offers/{offer.id}/',
        {'amount': '8000.00'},
        format='json',
    )

    assert response.status_code == 404


def test_expire_own_offer_returns_200(client):
    """El prestamista puede expirar su oferta."""
    user = create_approved_user()
    offer = OfferFactory(lender_user_id=user.id)
    authenticate(client, user)

    response = client.patch(
        f'/api/v1/offers/{offer.id}/',
        {'status': 'expired'},
        format='json',
    )

    assert response.status_code == 200
    assert response.data['status'] == 'expired'


def test_expire_already_expired_offer_returns_400(client):
    """Expirar una oferta que ya está expirada devuelve 400."""
    user = create_approved_user()
    offer = OfferFactory(lender_user_id=user.id, status='expired')
    authenticate(client, user)

    response = client.patch(
        f'/api/v1/offers/{offer.id}/',
        {'status': 'expired'},
        format='json',
    )

    assert response.status_code == 400


def test_expire_other_lender_offer_returns_404(client):
    """No se puede expirar la oferta de otro prestamista."""
    user = create_approved_user()
    other = create_approved_user(email='expirar-ajeno@example.com')
    offer = OfferFactory(lender_user_id=other.id)
    authenticate(client, user)

    response = client.patch(
        f'/api/v1/offers/{offer.id}/',
        {'status': 'expired'},
        format='json',
    )

    assert response.status_code == 404


def test_patch_expired_offer_returns_400(client):
    """Una oferta expirada no se puede modificar."""
    user = create_approved_user()
    offer = OfferFactory(lender_user_id=user.id, status='expired')
    authenticate(client, user)

    response = client.patch(
        f'/api/v1/offers/{offer.id}/',
        {'amount': '8000.00'},
        format='json',
    )

    assert response.status_code == 400


def test_patch_offer_with_invalid_amount_returns_400(client):
    """Actualizar con un monto no positivo devuelve 400."""
    user = create_approved_user()
    offer = OfferFactory(lender_user_id=user.id)
    authenticate(client, user)

    response = client.patch(
        f'/api/v1/offers/{offer.id}/',
        {'amount': '0.00'},
        format='json',
    )

    assert response.status_code == 400


def test_patch_offer_without_kyc_returns_403(client):
    """Sin KYC aprobada no se puede modificar una oferta."""
    from apps.identity.services import register_user

    user = register_user(email='patch-sin-kyc@example.com', password='TestPass123!')
    offer = OfferFactory(lender_user_id=user.id)
    authenticate(client, user)

    response = client.patch(
        f'/api/v1/offers/{offer.id}/',
        {'amount': '8000.00'},
        format='json',
    )

    assert response.status_code == 403


def test_patch_unknown_offer_returns_404(client):
    """Una oferta inexistente devuelve 404."""
    import uuid

    user = create_approved_user()
    authenticate(client, user)

    response = client.patch(
        f'/api/v1/offers/{uuid.uuid4()}/',
        {'amount': '8000.00'},
        format='json',
    )

    assert response.status_code == 404


def test_create_offer_without_kyc_is_blocked_by_the_permission(client):
    """Sin KYC publicar una oferta se corta con el 403 del permiso (AGENTS §9.9)."""
    from apps.identity.services import register_user

    user = register_user(email='sin-kyc-oferta@example.com', password='TestPass123!')
    authenticate(client, user)

    response = client.post(
        '/api/v1/offers/',
        {
            'amount': '10000.00',
            'currency': 'ARS',
            'interest_rate': '24.00',
            'term_months': 12,
        },
        format='json',
    )

    assert response.status_code == 403
    assert response.data['error']['code'] == 'permission_denied'
    assert response.data['error']['message'] == (
        'Necesitás completar la verificación KYC para realizar esta operación.'
    )


def test_list_offers_without_kyc_is_allowed(client):
    """Las lecturas no cambian: sin KYC se pueden listar las ofertas."""
    from apps.identity.services import register_user

    user = register_user(email='sin-kyc-oferta-lectura@example.com', password='TestPass123!')
    authenticate(client, user)

    response = client.get('/api/v1/offers/')

    assert response.status_code == 200
