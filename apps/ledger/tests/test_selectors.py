"""Tests de los selectores de lectura del ledger."""

import uuid
from decimal import Decimal

import pytest

from apps.ledger.tests.factories import AccountFactory, create_approved_user

pytestmark = pytest.mark.django_db


def test_get_account_for_user_returns_own_account():
    """El selector devuelve la cuenta del propio usuario."""
    from apps.ledger.selectors import get_account_for_user

    user = create_approved_user()
    account = AccountFactory(user_id=user.id)

    found = get_account_for_user(account_id=account.id, user_id=user.id)

    assert found is not None
    assert found.id == account.id


def test_get_account_for_user_returns_none_for_other_user():
    """El selector no expone cuentas de otros usuarios."""
    from apps.ledger.selectors import get_account_for_user

    user = create_approved_user()
    other = create_approved_user(email='ajeno@example.com')
    account = AccountFactory(user_id=other.id)

    assert get_account_for_user(account_id=account.id, user_id=user.id) is None


def test_list_accounts_for_user_returns_only_own_wallets():
    """El listado devuelve solo las billeteras del usuario."""
    from apps.ledger.selectors import list_accounts_for_user

    user = create_approved_user()
    other = create_approved_user(email='listado@example.com')
    AccountFactory(user_id=user.id)
    AccountFactory(user_id=other.id)

    accounts = list_accounts_for_user(user_id=user.id)

    assert [account.user_id for account in accounts] == [user.id]


def test_get_balance_returns_balance():
    """El selector de saldo devuelve el saldo de la cuenta."""
    from apps.ledger.selectors import get_balance

    user = create_approved_user()
    account = AccountFactory(user_id=user.id, balance=Decimal('42.50'))

    assert get_balance(account_id=account.id, user_id=user.id) == Decimal('42.50')


def test_get_balance_returns_none_for_other_user():
    """El selector de saldo no expone cuentas ajenas."""
    from apps.ledger.selectors import get_balance

    user = create_approved_user()
    other = create_approved_user(email='saldo@example.com')
    account = AccountFactory(user_id=other.id, balance=Decimal('42.50'))

    assert get_balance(account_id=account.id, user_id=user.id) is None


def test_list_transactions_for_user_returns_only_own_transactions():
    """El listado de transacciones solo expone las del usuario."""
    from apps.ledger.models import Account
    from apps.ledger.selectors import list_transactions_for_user
    from apps.ledger.services import deposit

    user = create_approved_user()
    other = create_approved_user(email='transacciones@example.com')
    deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('10.00'),
        idempotency_key='sel-1',
    )
    deposit(
        user_id=other.id,
        currency=Account.Currency.ARS,
        amount=Decimal('20.00'),
        idempotency_key='sel-2',
    )

    transactions = list_transactions_for_user(user_id=user.id)

    assert len(transactions) == 1
    assert transactions[0].created_by_user_id == user.id


def test_get_transaction_returns_none_for_other_user():
    """El selector de transacción no expone transacciones ajenas."""
    from apps.ledger.models import Account
    from apps.ledger.selectors import get_transaction
    from apps.ledger.services import deposit

    user = create_approved_user()
    other = create_approved_user(email='detalle@example.com')
    ledger_transaction = deposit(
        user_id=other.id,
        currency=Account.Currency.ARS,
        amount=Decimal('10.00'),
        idempotency_key='det-1',
    )

    assert get_transaction(transaction_id=ledger_transaction.id, user_id=user.id) is None


def test_get_transaction_returns_own_transaction():
    """El selector de transacción devuelve la propia."""
    from apps.ledger.models import Account
    from apps.ledger.selectors import get_transaction
    from apps.ledger.services import deposit

    user = create_approved_user()
    ledger_transaction = deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('10.00'),
        idempotency_key='det-2',
    )

    found = get_transaction(transaction_id=ledger_transaction.id, user_id=user.id)

    assert found is not None
    assert found.id == ledger_transaction.id
    assert found.id != uuid.uuid4()


def test_list_transactions_includes_incoming_movements():
    """El listado incluye los movimientos que tocan cuentas del usuario."""
    from apps.ledger.models import Account
    from apps.ledger.selectors import list_transactions_for_user
    from apps.ledger.services import create_user_wallet, deposit, transfer

    sender = create_approved_user()
    receiver = create_approved_user(email='receptor@example.com')
    deposit(
        user_id=sender.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='lista-emisor',
    )
    source = Account.objects.get(user_id=sender.id, kind=Account.Kind.USER_WALLET)
    destination = create_user_wallet(user_id=receiver.id, currency=Account.Currency.ARS)
    transfer(
        user_id=sender.id,
        source_account_id=source.id,
        destination_account_id=destination.id,
        amount=Decimal('30.00'),
        idempotency_key='lista-transferencia',
    )

    transactions = list_transactions_for_user(user_id=receiver.id)

    assert len(transactions) == 1
    assert transactions[0].destination_account_id == destination.id


def test_list_transactions_excludes_movements_of_other_users():
    """El listado no expone movimientos que no tocan cuentas del usuario."""
    from apps.ledger.models import Account
    from apps.ledger.selectors import list_transactions_for_user
    from apps.ledger.services import deposit

    user = create_approved_user()
    other = create_approved_user(email='ajeno-lista@example.com')
    deposit(
        user_id=other.id,
        currency=Account.Currency.ARS,
        amount=Decimal('50.00'),
        idempotency_key='lista-ajena',
    )

    assert list(list_transactions_for_user(user_id=user.id)) == []
