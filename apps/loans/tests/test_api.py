"""Tests de la API de loans."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.loans.tests.factories import create_approved_user

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


def fund_user(user_id, amount='10000.00', key='fund'):
    """Deposita fondos simulados en la billetera del usuario."""
    from apps.ledger.services import deposit

    return deposit(
        user_id=user_id,
        currency='ARS',
        amount=Decimal(amount),
        idempotency_key=key,
    )


def make_offer(lender_user_id, amount='10000.00'):
    """Crea una oferta activa del prestamista."""
    from apps.offers.services import create_offer

    return create_offer(
        lender_user_id=lender_user_id,
        amount=Decimal(amount),
        currency='ARS',
        interest_rate=Decimal('24.00'),
        term_months=12,
    )


def test_loans_list_requires_authentication(client):
    """El listado de préstamos exige autenticación."""
    response = client.get('/api/v1/loans/')

    assert response.status_code == 401
    assert response.data['error']['code'] == 'not_authenticated'


def test_loans_list_returns_loans_as_borrower_or_lender(client):
    """El listado devuelve los préstamos en los que el usuario es parte."""
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='lista-prestamista@example.com')
    borrower = create_approved_user(email='lista-prestatario@example.com')
    third = create_approved_user(email='lista-tercero@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-lista')
    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='lista-accept',
    )

    authenticate(client, borrower)
    response = client.get('/api/v1/loans/')
    assert [item['id'] for item in response.data['results']] == [str(loan.id)]

    authenticate(client, lender)
    response = client.get('/api/v1/loans/')
    assert [item['id'] for item in response.data['results']] == [str(loan.id)]

    authenticate(client, third)
    response = client.get('/api/v1/loans/')
    assert response.data['results'] == []


def test_accept_offer_returns_201(client):
    """Aceptar una oferta por API devuelve 201 con el préstamo."""
    lender = create_approved_user(email='api-prestamista@example.com')
    borrower = create_approved_user(email='api-prestatario@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-api')
    authenticate(client, borrower)

    response = client.post(
        '/api/v1/loans/',
        {'offer_id': str(offer.id)},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-accept-1',
    )

    assert response.status_code == 201
    assert response.data['status'] == 'active'
    assert response.data['borrower_user_id'] == str(borrower.id)


def test_accept_offer_without_idempotency_key_returns_400(client):
    """Sin header Idempotency-Key el POST devuelve 400."""
    lender = create_approved_user(email='api-sin-key-prestamista@example.com')
    borrower = create_approved_user(email='api-sin-key-prestatario@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-sin-key')
    authenticate(client, borrower)

    response = client.post('/api/v1/loans/', {'offer_id': str(offer.id)}, format='json')

    assert response.status_code == 400


def test_accept_offer_same_key_returns_the_original(client):
    """La misma clave de idempotencia devuelve el préstamo original."""
    lender = create_approved_user(email='api-idem-prestamista@example.com')
    borrower = create_approved_user(email='api-idem-prestatario@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-idem')
    authenticate(client, borrower)

    first = client.post(
        '/api/v1/loans/',
        {'offer_id': str(offer.id)},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-idem',
    )
    second = client.post(
        '/api/v1/loans/',
        {'offer_id': str(offer.id)},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-idem',
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.data['id'] == second.data['id']


def test_accept_offer_same_key_different_offer_returns_409(client):
    """La misma clave con otra oferta devuelve 409."""
    lender = create_approved_user(email='api-conflict-prestamista@example.com')
    borrower = create_approved_user(email='api-conflict-prestatario@example.com')
    first_offer = make_offer(lender.id, amount='10000.00')
    second_offer = make_offer(lender.id, amount='20000.00')
    fund_user(lender.id, amount='30000.00', key='fund-conflict')
    authenticate(client, borrower)

    client.post(
        '/api/v1/loans/',
        {'offer_id': str(first_offer.id)},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-conflict',
    )
    response = client.post(
        '/api/v1/loans/',
        {'offer_id': str(second_offer.id)},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-conflict',
    )

    assert response.status_code == 409
    assert response.data['error']['code'] == 'idempotency_conflict'


def test_accept_offer_requires_approved_kyc(client):
    """Sin KYC aprobada el POST devuelve 403."""
    from apps.identity.services import register_user

    lender = create_approved_user(email='api-kyc-prestamista@example.com')
    borrower = register_user(email='api-kyc-prestatario@example.com', password='TestPass123!')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-kyc')
    authenticate(client, borrower)

    response = client.post(
        '/api/v1/loans/',
        {'offer_id': str(offer.id)},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-kyc',
    )

    assert response.status_code == 403


def test_loan_detail_of_party_returns_snapshot_and_installments(client):
    """El detalle devuelve el snapshot y las cuotas para las partes."""
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='detalle-prestamista@example.com')
    borrower = create_approved_user(email='detalle-prestatario@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-detalle')
    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='detalle-accept',
    )
    authenticate(client, borrower)

    response = client.get(f'/api/v1/loans/{loan.id}/')

    assert response.status_code == 200
    assert response.data['id'] == str(loan.id)
    assert response.data['terms_snapshot']['snapshot_data']['term_months'] == 12
    assert len(response.data['installments']) == 12


def test_loan_detail_of_third_party_returns_404(client):
    """Un tercero no puede ver el préstamo."""
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='tercero-prestamista@example.com')
    borrower = create_approved_user(email='tercero-prestatario@example.com')
    third = create_approved_user(email='tercero-observador@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-tercero')
    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='tercero-accept',
    )
    authenticate(client, third)

    response = client.get(f'/api/v1/loans/{loan.id}/')

    assert response.status_code == 404
    assert response.data['error']['code'] == 'not_found'


def test_pay_installment_returns_200(client):
    """Pagar una cuota devuelve 200 con la cuota pagada."""
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='pago-prestamista@example.com')
    borrower = create_approved_user(email='pago-prestatario@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-pago')
    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='pago-accept',
    )
    authenticate(client, borrower)

    response = client.post(f'/api/v1/loans/{loan.id}/installments/1/pay/')

    assert response.status_code == 200
    assert response.data['status'] == 'paid'


def test_pay_installment_of_third_party_returns_404(client):
    """Un tercero no puede pagar cuotas."""
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='pago-tercero-prestamista@example.com')
    borrower = create_approved_user(email='pago-tercero-prestatario@example.com')
    third = create_approved_user(email='pago-tercero-observador@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-pago-tercero')
    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='pago-tercero-accept',
    )
    authenticate(client, third)

    response = client.post(f'/api/v1/loans/{loan.id}/installments/1/pay/')

    assert response.status_code == 404


def test_pay_installment_out_of_order_returns_400(client):
    """Pagar una cuota fuera de orden devuelve 400."""
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='orden-prestamista@example.com')
    borrower = create_approved_user(email='orden-prestatario@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-orden')
    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='orden-accept',
    )
    authenticate(client, borrower)

    response = client.post(f'/api/v1/loans/{loan.id}/installments/2/pay/')

    assert response.status_code == 400


def test_pay_unknown_installment_returns_404(client):
    """Una cuota inexistente devuelve 404."""
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='cuota-prestamista@example.com')
    borrower = create_approved_user(email='cuota-prestatario@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-cuota')
    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='cuota-accept',
    )
    authenticate(client, borrower)

    response = client.post(f'/api/v1/loans/{loan.id}/installments/99/pay/')

    assert response.status_code == 404
