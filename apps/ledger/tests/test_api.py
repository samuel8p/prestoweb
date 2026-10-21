"""Tests de la API del ledger."""

import uuid
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.ledger.tests.factories import AccountFactory, create_approved_user

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


def test_accounts_list_requires_authentication(client):
    """El listado de cuentas exige autenticación."""
    response = client.get('/api/v1/ledger/accounts/')

    assert response.status_code == 401
    assert response.data['error']['code'] == 'not_authenticated'


def test_accounts_list_returns_only_own_accounts(client):
    """El listado devuelve solo las cuentas del usuario autenticado."""
    user = create_approved_user()
    other = create_approved_user(email='cuentas@example.com')
    AccountFactory(user_id=user.id)
    AccountFactory(user_id=other.id)
    authenticate(client, user)

    response = client.get('/api/v1/ledger/accounts/')

    assert response.status_code == 200
    assert [account['user_id'] for account in response.data['results']] == [str(user.id)]


def test_create_account_creates_user_wallet(client):
    """Crear una cuenta devuelve la billetera del usuario."""
    user = create_approved_user()
    authenticate(client, user)

    response = client.post('/api/v1/ledger/accounts/', {'currency': 'ARS'}, format='json')

    assert response.status_code == 201
    assert response.data['currency'] == 'ARS'
    assert response.data['kind'] == 'user_wallet'
    assert response.data['balance'] == '0.00'


def test_create_account_rejects_invalid_currency(client):
    """Una moneda inexistente devuelve 400."""
    user = create_approved_user()
    authenticate(client, user)

    response = client.post('/api/v1/ledger/accounts/', {'currency': 'EUR'}, format='json')

    assert response.status_code == 400
    assert response.data['error']['code'] == 'validation_error'


def test_account_balance_returns_balance(client):
    """El endpoint de balance devuelve el saldo de la cuenta propia."""
    user = create_approved_user()
    account = AccountFactory(user_id=user.id, balance=Decimal('75.25'))
    authenticate(client, user)

    response = client.get(f'/api/v1/ledger/accounts/{account.id}/balance/')

    assert response.status_code == 200
    assert response.data['balance'] == '75.25'


def test_account_balance_of_other_user_returns_404(client):
    """No se puede consultar el balance de la cuenta de otro usuario."""
    user = create_approved_user()
    other = create_approved_user(email='balance@example.com')
    account = AccountFactory(user_id=other.id, balance=Decimal('75.25'))
    authenticate(client, user)

    response = client.get(f'/api/v1/ledger/accounts/{account.id}/balance/')

    assert response.status_code == 404
    assert response.data['error']['code'] == 'not_found'


def test_create_deposit_returns_201(client):
    """El depósito devuelve 201 con la transacción creada."""
    user = create_approved_user()
    authenticate(client, user)

    response = client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'deposit', 'currency': 'ARS', 'amount': '100.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-dep-1',
    )

    assert response.status_code == 201
    assert response.data['type'] == 'deposit'


def test_create_deposit_without_idempotency_key_returns_400(client):
    """Sin header Idempotency-Key el depósito devuelve 400."""
    user = create_approved_user()
    authenticate(client, user)

    response = client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'deposit', 'currency': 'ARS', 'amount': '100.00'},
        format='json',
    )

    assert response.status_code == 400


def test_create_deposit_same_key_different_amount_returns_409(client):
    """La misma clave con otro payload devuelve 409."""
    user = create_approved_user()
    authenticate(client, user)

    client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'deposit', 'currency': 'ARS', 'amount': '100.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-conflict',
    )
    response = client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'deposit', 'currency': 'ARS', 'amount': '250.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-conflict',
    )

    assert response.status_code == 409
    assert response.data['error']['code'] == 'idempotency_conflict'


def test_create_deposit_requires_approved_kyc(client):
    """Sin KYC aprobada el depósito devuelve 403."""
    from apps.ledger.tests.factories import create_identity_user

    user = create_identity_user()
    authenticate(client, user)

    response = client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'deposit', 'currency': 'ARS', 'amount': '100.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-kyc',
    )

    assert response.status_code == 403


def test_create_transfer_returns_201(client):
    """La transferencia entre billeteras propias devuelve 201."""
    user = create_approved_user()
    other = create_approved_user(email='destino@example.com')
    source = AccountFactory(user_id=user.id, balance=Decimal('100.00'))
    destination = AccountFactory(user_id=other.id, balance=Decimal('0.00'))
    authenticate(client, user)

    response = client.post(
        '/api/v1/ledger/transactions/',
        {
            'type': 'transfer',
            'currency': 'ARS',
            'amount': '25.00',
            'destination_account_id': str(destination.id),
        },
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-tra-1',
    )

    assert response.status_code == 201
    source.refresh_from_db()
    destination.refresh_from_db()
    assert source.balance == Decimal('75.00')
    assert destination.balance == Decimal('25.00')


def test_create_transaction_with_invalid_type_returns_400(client):
    """Un tipo de movimiento no válido devuelve 400."""
    user = create_approved_user()
    authenticate(client, user)

    response = client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'reversal', 'currency': 'ARS', 'amount': '10.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-bad-type',
    )

    assert response.status_code == 400


def test_list_transactions_returns_only_own(client):
    """El listado de transacciones solo expone las del usuario."""
    user = create_approved_user()
    other = create_approved_user(email='listado-tx@example.com')
    authenticate(client, user)
    for index in range(2):
        client.post(
            '/api/v1/ledger/transactions/',
            {'type': 'deposit', 'currency': 'ARS', 'amount': '10.00'},
            format='json',
            HTTP_IDEMPOTENCY_KEY=f'api-list-{index}',
        )
    other_client = APIClient()
    authenticate(other_client, other)
    other_client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'deposit', 'currency': 'ARS', 'amount': '10.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-list-other',
    )

    response = client.get('/api/v1/ledger/transactions/')

    assert response.status_code == 200
    assert len(response.data['results']) == 2
    assert all(
        transaction['created_by_user_id'] == str(user.id)
        for transaction in response.data['results']
    )


def test_transaction_detail_of_other_user_returns_404(client):
    """No se puede ver la transacción de otro usuario."""
    from apps.ledger.models import Account
    from apps.ledger.services import deposit

    user = create_approved_user()
    other = create_approved_user(email='detalle-tx@example.com')
    ledger_transaction = deposit(
        user_id=other.id,
        currency=Account.Currency.ARS,
        amount=Decimal('10.00'),
        idempotency_key='detalle-api',
    )
    authenticate(client, user)

    response = client.get(f'/api/v1/ledger/transactions/{ledger_transaction.id}/')

    assert response.status_code == 404
    assert response.data['error']['code'] == 'not_found'


def test_transaction_detail_of_own_transaction_returns_200(client):
    """El usuario ve su propia transacción."""
    from apps.ledger.models import Account
    from apps.ledger.services import deposit

    user = create_approved_user()
    ledger_transaction = deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('10.00'),
        idempotency_key='detalle-api-2',
    )
    authenticate(client, user)

    response = client.get(f'/api/v1/ledger/transactions/{ledger_transaction.id}/')

    assert response.status_code == 200
    assert response.data['id'] == str(ledger_transaction.id)
    assert response.data['id'] != str(uuid.uuid4())
