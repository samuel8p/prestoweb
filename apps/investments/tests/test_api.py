"""Tests de la API de investments."""

import uuid
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.investments.tests.factories import (
    InvestmentProductFactory,
    create_approved_user,
    fund_user,
)

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


def test_products_list_requires_authentication(client):
    """El listado de productos exige autenticación."""
    response = client.get('/api/v1/investments/products/')

    assert response.status_code == 401
    assert response.data['error']['code'] == 'not_authenticated'


def test_products_list_returns_only_active_products(client):
    """Solo se listan los productos activos."""
    from apps.investments.models import InvestmentProduct

    user = create_approved_user()
    InvestmentProductFactory(status=InvestmentProduct.Status.ACTIVE)
    InvestmentProductFactory(status=InvestmentProduct.Status.CANCELLED)
    authenticate(client, user)

    response = client.get('/api/v1/investments/products/')

    assert response.status_code == 200
    assert len(response.data['results']) == 1
    assert response.data['results'][0]['status'] == 'active'


def test_positions_list_requires_authentication(client):
    """El listado de posiciones exige autenticación."""
    response = client.get('/api/v1/investments/positions/')

    assert response.status_code == 401


def test_positions_list_returns_only_own_positions(client):
    """El listado devuelve solo las posiciones del usuario."""
    from apps.investments.services import open_position

    user = create_approved_user()
    other = create_approved_user(email='posiciones-ajenas@example.com')
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='api-pos-dep')
    open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='api-pos-open',
    )
    authenticate(client, other)

    response = client.get('/api/v1/investments/positions/')

    assert response.status_code == 200
    assert response.data['results'] == []


def test_open_position_returns_201(client):
    """Abrir una inversión por API devuelve 201 con la posición."""
    user = create_approved_user()
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='api-open-dep')
    authenticate(client, user)

    response = client.post(
        '/api/v1/investments/positions/',
        {'product_id': str(product.id), 'amount': '5000.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-open-1',
    )

    assert response.status_code == 201
    assert response.data['status'] == 'active'
    assert response.data['amount'] == '5000.00'
    assert response.data['interest_amount'] == '49.32'


def test_open_position_without_idempotency_key_returns_400(client):
    """Sin header Idempotency-Key el POST devuelve 400."""
    user = create_approved_user()
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='api-open-dep-2')
    authenticate(client, user)

    response = client.post(
        '/api/v1/investments/positions/',
        {'product_id': str(product.id), 'amount': '5000.00'},
        format='json',
    )

    assert response.status_code == 400


def test_open_position_same_key_returns_the_original(client):
    """La misma clave de idempotencia devuelve la posición original."""
    user = create_approved_user()
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='api-open-dep-3')
    authenticate(client, user)

    first = client.post(
        '/api/v1/investments/positions/',
        {'product_id': str(product.id), 'amount': '5000.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-open-idem',
    )
    second = client.post(
        '/api/v1/investments/positions/',
        {'product_id': str(product.id), 'amount': '5000.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-open-idem',
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.data['id'] == second.data['id']


def test_open_position_same_key_different_product_returns_409(client):
    """La misma clave con otro producto devuelve 409."""
    user = create_approved_user()
    first_product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    second_product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='20000.00', key='api-open-dep-4')
    authenticate(client, user)

    client.post(
        '/api/v1/investments/positions/',
        {'product_id': str(first_product.id), 'amount': '5000.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-open-conflict',
    )
    response = client.post(
        '/api/v1/investments/positions/',
        {'product_id': str(second_product.id), 'amount': '5000.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-open-conflict',
    )

    assert response.status_code == 409
    assert response.data['error']['code'] == 'idempotency_conflict'


def test_open_position_requires_approved_kyc(client):
    """Sin KYC aprobada el POST devuelve 403."""
    from apps.identity.services import register_user

    user = register_user(email='api-inv-sin-kyc@example.com', password='TestPass123!')
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    authenticate(client, user)

    response = client.post(
        '/api/v1/investments/positions/',
        {'product_id': str(product.id), 'amount': '5000.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-open-kyc',
    )

    assert response.status_code == 403


def test_open_position_below_minimum_returns_400(client):
    """Un monto menor al mínimo devuelve 400."""
    user = create_approved_user()
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='api-open-dep-6')
    authenticate(client, user)

    response = client.post(
        '/api/v1/investments/positions/',
        {'product_id': str(product.id), 'amount': '100.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-open-min',
    )

    assert response.status_code == 400


def test_position_detail_of_owner_returns_200(client):
    """El titular ve el detalle de su posición."""
    from apps.investments.services import open_position

    user = create_approved_user()
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='api-open-dep-7')
    position = open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='api-open-detail',
    )
    authenticate(client, user)

    response = client.get(f'/api/v1/investments/positions/{position.id}/')

    assert response.status_code == 200
    assert response.data['id'] == str(position.id)
    assert response.data['product'] == product.id
    assert response.data['product_detail']['term_days'] == product.term_days


def test_position_detail_of_third_party_returns_404(client):
    """Un tercero no puede ver la posición."""
    from apps.investments.services import open_position

    user = create_approved_user()
    third = create_approved_user(email='api-inv-tercero@example.com')
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='api-open-dep-8')
    position = open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='api-open-third',
    )
    authenticate(client, third)

    response = client.get(f'/api/v1/investments/positions/{position.id}/')

    assert response.status_code == 404
    assert response.data['error']['code'] == 'not_found'


def test_position_detail_of_unknown_position_returns_404(client):
    """Una posición inexistente devuelve 404."""
    user = create_approved_user()
    authenticate(client, user)

    response = client.get(f'/api/v1/investments/positions/{uuid.uuid4()}/')

    assert response.status_code == 404
