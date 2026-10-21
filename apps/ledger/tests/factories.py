import uuid
from decimal import Decimal

import factory

from apps.ledger.models import Account, LedgerEntry, LedgerTransaction


class AccountFactory(factory.django.DjangoModelFactory):
    """Factory de Account."""

    class Meta:
        model = Account

    user_id = factory.LazyFunction(uuid.uuid4)
    currency = Account.Currency.ARS
    kind = Account.Kind.USER_WALLET
    balance = Decimal('0.00')


class LedgerTransactionFactory(factory.django.DjangoModelFactory):
    """Factory de LedgerTransaction."""

    class Meta:
        model = LedgerTransaction

    type = LedgerTransaction.Type.DEPOSIT
    idempotency_key = factory.Sequence(lambda n: f'key-{n}')
    request_hash = factory.Sequence(lambda n: f'hash-{n}')
    created_by_user_id = factory.LazyFunction(uuid.uuid4)
    description = ''


class LedgerEntryFactory(factory.django.DjangoModelFactory):
    """Factory de LedgerEntry."""

    class Meta:
        model = LedgerEntry

    ledger_transaction = factory.SubFactory(LedgerTransactionFactory)
    account = factory.SubFactory(AccountFactory)
    direction = LedgerEntry.Direction.DEBIT
    amount = Decimal('10.00')
    currency = Account.Currency.ARS
