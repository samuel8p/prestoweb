"""Tests de API de retiros y transferencias del ledger, con errores y acceso cruzado."""

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


def test_create_withdrawal_returns_201(client):
    """El retiro devuelve 201 y descuenta el saldo."""
    user = create_approved_user()
    authenticate(client, user)
    client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'deposit', 'currency': 'ARS', 'amount': '100.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-ret-dep',
    )

    response = client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'withdrawal', 'currency': 'ARS', 'amount': '40.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-ret-1',
    )

    assert response.status_code == 201
    assert response.data['type'] == 'withdrawal'


def test_create_withdrawal_without_funds_returns_400(client):
    """Un retiro sin saldo suficiente devuelve 400."""
    user = create_approved_user()
    authenticate(client, user)
    client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'deposit', 'currency': 'ARS', 'amount': '10.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-ret-dep-2',
    )

    response = client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'withdrawal', 'currency': 'ARS', 'amount': '500.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-ret-2',
    )

    assert response.status_code == 400
    assert response.data['error']['code'] == 'validation_error'


def test_create_withdrawal_requires_approved_kyc(client):
    """Sin KYC aprobada el retiro devuelve 403."""
    from apps.ledger.tests.factories import create_identity_user

    user = create_identity_user()
    authenticate(client, user)

    response = client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'withdrawal', 'currency': 'ARS', 'amount': '10.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-ret-kyc',
    )

    assert response.status_code == 403
    assert response.data['error']['code'] == 'permission_denied'


def test_create_withdrawal_without_idempotency_key_returns_400(client):
    """Sin header Idempotency-Key el retiro devuelve 400."""
    user = create_approved_user()
    authenticate(client, user)

    response = client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'withdrawal', 'currency': 'ARS', 'amount': '10.00'},
        format='json',
    )

    assert response.status_code == 400


def test_create_withdrawal_fails_when_simulated_deposits_disabled(client, settings):
    """Con los depósitos simulados deshabilitados el retiro devuelve 400."""
    settings.LEDGER_SIMULATED_DEPOSITS_ENABLED = False
    user = create_approved_user()
    authenticate(client, user)

    response = client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'withdrawal', 'currency': 'ARS', 'amount': '10.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-ret-off',
    )

    assert response.status_code == 400


def test_create_transfer_without_destination_returns_400(client):
    """Una transferencia sin cuenta destino devuelve 400."""
    user = create_approved_user()
    authenticate(client, user)

    response = client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'transfer', 'currency': 'ARS', 'amount': '10.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-tra-sin-destino',
    )

    assert response.status_code == 400
    assert 'destination_account_id' in str(response.data['error']['details'])


def test_create_transfer_without_wallet_in_currency_returns_400(client):
    """Sin billetera en esa moneda la transferencia devuelve 400."""
    user = create_approved_user()
    destination = AccountFactory(
        user_id=uuid.uuid4(),
        currency='USD',
        kind='user_wallet',
        balance=Decimal('0.00'),
    )
    authenticate(client, user)

    response = client.post(
        '/api/v1/ledger/transactions/',
        {
            'type': 'transfer',
            'currency': 'USD',
            'amount': '10.00',
            'destination_account_id': str(destination.id),
        },
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-tra-sin-billetera',
    )

    assert response.status_code == 400


def test_create_transfer_to_other_currency_returns_400(client):
    """Una transferencia a otra moneda devuelve 400."""
    user = create_approved_user()
    AccountFactory(
        user_id=user.id,
        currency='ARS',
        kind='user_wallet',
        balance=Decimal('100.00'),
    )
    destination = AccountFactory(
        user_id=uuid.uuid4(),
        currency='USD',
        kind='user_wallet',
        balance=Decimal('0.00'),
    )
    authenticate(client, user)

    response = client.post(
        '/api/v1/ledger/transactions/',
        {
            'type': 'transfer',
            'currency': 'ARS',
            'amount': '10.00',
            'destination_account_id': str(destination.id),
        },
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-tra-moneda',
    )

    assert response.status_code == 400


def test_create_transfer_to_non_wallet_destination_returns_400(client):
    """Una transferencia a una cuenta que no es user_wallet devuelve 400."""
    user = create_approved_user()
    AccountFactory(
        user_id=user.id,
        currency='ARS',
        kind='user_wallet',
        balance=Decimal('100.00'),
    )
    destination = AccountFactory(
        user_id=None,
        currency='ARS',
        kind='custody',
        balance=Decimal('0.00'),
    )
    authenticate(client, user)

    response = client.post(
        '/api/v1/ledger/transactions/',
        {
            'type': 'transfer',
            'currency': 'ARS',
            'amount': '10.00',
            'destination_account_id': str(destination.id),
        },
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-tra-kind',
    )

    assert response.status_code == 400


def test_create_transfer_cannot_use_another_user_source_account(client):
    """No se puede transferir usando la cuenta de otro usuario (acceso cruzado)."""
    user = create_approved_user()
    other = create_approved_user(email='ajeno-transferencia@example.com')
    AccountFactory(
        user_id=other.id,
        currency='ARS',
        kind='user_wallet',
        balance=Decimal('100.00'),
    )
    destination = AccountFactory(
        user_id=user.id,
        currency='ARS',
        kind='user_wallet',
        balance=Decimal('0.00'),
    )
    authenticate(client, user)

    response = client.post(
        '/api/v1/ledger/transactions/',
        {
            'type': 'transfer',
            'currency': 'ARS',
            'amount': '10.00',
            'destination_account_id': str(destination.id),
        },
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-tra-ajena',
    )

    assert response.status_code == 400


def test_create_transfer_without_balance_returns_400(client):
    """Una transferencia sin saldo suficiente devuelve 400."""
    user = create_approved_user()
    AccountFactory(
        user_id=user.id,
        currency='ARS',
        kind='user_wallet',
        balance=Decimal('5.00'),
    )
    destination = AccountFactory(
        user_id=uuid.uuid4(),
        currency='ARS',
        kind='user_wallet',
        balance=Decimal('0.00'),
    )
    authenticate(client, user)

    response = client.post(
        '/api/v1/ledger/transactions/',
        {
            'type': 'transfer',
            'currency': 'ARS',
            'amount': '50.00',
            'destination_account_id': str(destination.id),
        },
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-tra-sin-saldo',
    )

    assert response.status_code == 400


def test_create_transaction_with_invalid_currency_returns_400(client):
    """Una moneda inválida devuelve 400."""
    user = create_approved_user()
    authenticate(client, user)

    response = client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'deposit', 'currency': 'EUR', 'amount': '10.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-moneda',
    )

    assert response.status_code == 400
    assert response.data['error']['code'] == 'validation_error'


def test_create_transaction_with_invalid_amount_returns_400(client):
    """Un importe no positivo devuelve 400."""
    user = create_approved_user()
    authenticate(client, user)

    response = client.post(
        '/api/v1/ledger/transactions/',
        {'type': 'deposit', 'currency': 'ARS', 'amount': '0.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='api-importe',
    )

    assert response.status_code == 400


def test_transaction_detail_of_another_user_movement_returns_404(client):
    """Un movimiento que solo toca cuentas de otro usuario devuelve 404."""
    from apps.ledger.models import Account
    from apps.ledger.services import create_user_wallet, deposit, transfer

    sender = create_approved_user()
    receiver = create_approved_user(email='detalle-receptor@example.com')
    deposit(
        user_id=sender.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='detalle-empisor',
    )
    source = Account.objects.get(user_id=sender.id, kind=Account.Kind.USER_WALLET)
    destination = create_user_wallet(user_id=receiver.id, currency=Account.Currency.ARS)
    transfer(
        user_id=sender.id,
        source_account_id=source.id,
        destination_account_id=destination.id,
        amount=Decimal('10.00'),
        idempotency_key='detalle-transferencia',
    )
    third = create_approved_user(email='detalle-tercero@example.com')
    authenticate(client, third)

    response = client.get(f'/api/v1/ledger/transactions/{destination.id}/')

    assert response.status_code == 404
