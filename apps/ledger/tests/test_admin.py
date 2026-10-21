"""Tests de la administración de Django para la app ledger."""

from decimal import Decimal

import pytest

from apps.ledger.tests.factories import create_approved_user

pytestmark = pytest.mark.django_db


def test_admin_reverse_action_creates_reversal(admin_client):
    """La acción de admin crea la transacción de reversión."""
    from apps.ledger.models import Account
    from apps.ledger.services import deposit

    user = create_approved_user()
    original = deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='admin-rev-1',
    )

    response = admin_client.post(
        '/admin/ledger/ledgertransaction/',
        {
            'action': 'reverse_transactions',
            '_selected_action': [str(original.id)],
        },
        follow=True,
    )

    assert response.status_code == 200
    reversal = original.reversal
    assert reversal.type == 'reversal'
    assert reversal.reverses_id == original.id


def test_admin_reverse_action_restores_the_balance(admin_client):
    """Después del reverso la billetera vuelve al saldo anterior."""
    from apps.ledger.models import Account
    from apps.ledger.services import deposit

    user = create_approved_user()
    original = deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='admin-rev-2',
    )

    admin_client.post(
        '/admin/ledger/ledgertransaction/',
        {
            'action': 'reverse_transactions',
            '_selected_action': [str(original.id)],
        },
        follow=True,
    )

    wallet = Account.objects.get(user_id=user.id, kind=Account.Kind.USER_WALLET)
    assert wallet.balance == Decimal('0.00')


def test_admin_reverse_action_skips_already_reversed(admin_client):
    """La acción de admin no rompe con transacciones ya reversadas."""
    from apps.ledger.models import Account
    from apps.ledger.services import deposit

    user = create_approved_user()
    original = deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='admin-rev-3',
    )
    admin_client.post(
        '/admin/ledger/ledgertransaction/',
        {
            'action': 'reverse_transactions',
            '_selected_action': [str(original.id)],
        },
        follow=True,
    )

    response = admin_client.post(
        '/admin/ledger/ledgertransaction/',
        {
            'action': 'reverse_transactions',
            '_selected_action': [str(original.id)],
        },
        follow=True,
    )

    assert response.status_code == 200
    assert original.reversal.type == 'reversal'
