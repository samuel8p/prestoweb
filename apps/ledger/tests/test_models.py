"""Tests de los modelos del ledger."""

import uuid
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.ledger.tests.factories import (
    AccountFactory,
    LedgerEntryFactory,
    LedgerTransactionFactory,
)

pytestmark = pytest.mark.django_db


def test_account_defaults_to_zero_balance():
    """Una cuenta arranca en cero."""
    from apps.ledger.models import Account

    account = AccountFactory()

    assert account.balance == Decimal('0.00')
    assert account.kind == Account.Kind.USER_WALLET


def test_user_wallet_requires_user_id():
    """Una user_wallet necesita un user_id."""
    from apps.ledger.models import Account

    with pytest.raises(IntegrityError):
        Account.objects.create(
            user_id=None,
            currency=Account.Currency.ARS,
            kind=Account.Kind.USER_WALLET,
            balance=Decimal('0.00'),
        )


def test_counterpart_account_requires_null_user_id():
    """Las cuentas de contrapartida no tienen user_id."""
    from apps.ledger.models import Account

    with pytest.raises(IntegrityError):
        Account.objects.create(
            user_id=uuid.uuid4(),
            currency=Account.Currency.ARS,
            kind=Account.Kind.CUSTODY,
            balance=Decimal('0.00'),
        )


def test_only_one_user_wallet_per_user_and_currency():
    """Un usuario tiene una sola user_wallet por moneda."""
    from apps.ledger.models import Account

    user_id = uuid.uuid4()
    AccountFactory(user_id=user_id, currency=Account.Currency.ARS)

    with pytest.raises(IntegrityError):
        AccountFactory(user_id=user_id, currency=Account.Currency.ARS)


def test_user_wallet_per_currency_allows_different_currencies():
    """Un usuario puede tener una user_wallet por moneda."""
    from apps.ledger.models import Account

    user_id = uuid.uuid4()
    AccountFactory(user_id=user_id, currency=Account.Currency.ARS)
    AccountFactory(user_id=user_id, currency=Account.Currency.USD)

    assert Account.objects.filter(user_id=user_id, kind=Account.Kind.USER_WALLET).count() == 2


def test_only_one_counterpart_per_kind_and_currency():
    """Existe una sola cuenta de contrapartida por tipo y moneda."""
    from apps.ledger.models import Account

    AccountFactory(user_id=None, currency=Account.Currency.ARS, kind=Account.Kind.CUSTODY)

    with pytest.raises(IntegrityError):
        AccountFactory(
            user_id=None,
            currency=Account.Currency.ARS,
            kind=Account.Kind.CUSTODY,
        )


def test_user_wallet_balance_cannot_be_negative():
    """Una user_wallet no puede quedar con saldo negativo."""
    from apps.ledger.models import Account

    with pytest.raises(IntegrityError):
        AccountFactory(
            kind=Account.Kind.USER_WALLET,
            balance=Decimal('-1.00'),
        )


def test_counterpart_account_balance_can_be_negative():
    """Las cuentas de contrapartida pueden quedar negativas."""
    from apps.ledger.models import Account

    account = AccountFactory(
        user_id=None,
        kind=Account.Kind.CUSTODY,
        balance=Decimal('-100.00'),
    )

    assert account.balance == Decimal('-100.00')


def test_account_currency_must_be_ars_or_usd():
    """Una cuenta no puede tener una moneda que no sea ARS o USD."""
    from apps.ledger.models import Account

    with pytest.raises(IntegrityError):
        AccountFactory(currency='EUR')


def test_account_currency_is_case_sensitive():
    """La moneda en minúscula no es la misma moneda (los reportes comparan con `ARS`)."""
    from apps.ledger.models import Account

    with pytest.raises(IntegrityError):
        AccountFactory(currency='ars')


def test_account_accepts_both_project_currencies():
    """ARS y USD son las dos monedas válidas."""
    from apps.ledger.models import Account

    for currency in (Account.Currency.ARS, Account.Currency.USD):
        account = AccountFactory(currency=currency)

        assert account.currency == currency


def test_entry_currency_must_be_ars_or_usd():
    """Un asiento no puede tener una moneda que no sea ARS o USD."""
    from apps.ledger.models import Account

    with pytest.raises(IntegrityError):
        LedgerEntryFactory(currency='EUR')


def test_idempotency_key_is_unique_per_user():
    """La clave de idempotencia es única por usuario."""
    from apps.ledger.models import LedgerTransaction

    user_id = uuid.uuid4()
    LedgerTransactionFactory(created_by_user_id=user_id, idempotency_key='k1')

    with pytest.raises(IntegrityError):
        LedgerTransactionFactory(created_by_user_id=user_id, idempotency_key='k1')


def test_idempotency_key_can_repeat_for_another_user():
    """Dos usuarios distintos pueden usar la misma clave de idempotencia."""
    from apps.ledger.models import LedgerTransaction

    LedgerTransactionFactory(created_by_user_id=uuid.uuid4(), idempotency_key='k1')
    LedgerTransactionFactory(created_by_user_id=uuid.uuid4(), idempotency_key='k1')

    assert LedgerTransaction.objects.filter(idempotency_key='k1').count() == 2


def test_only_one_reversal_per_transaction():
    """Una transacción original admite un solo reverso."""
    from apps.ledger.models import LedgerTransaction

    original = LedgerTransactionFactory()
    LedgerTransactionFactory(reverses=original)

    with pytest.raises(IntegrityError):
        LedgerTransactionFactory(reverses=original)


def test_entry_amount_must_be_positive():
    """El importe de un asiento debe ser mayor que cero."""
    from apps.ledger.models import LedgerEntry

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LedgerEntryFactory(amount=Decimal('0.00'))

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LedgerEntryFactory(amount=Decimal('-5.00'))


def test_entry_direction_choices():
    """Un asiento es débito o crédito."""
    from apps.ledger.models import LedgerEntry

    assert LedgerEntry.Direction.DEBIT == 'debit'
    assert LedgerEntry.Direction.CREDIT == 'credit'
