import uuid
from decimal import Decimal

import factory
from django.db import transaction

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
    """Factory de LedgerEntry.

    Crea el asiento **y su contrapartida** para que la transacción quede
    balanceada: el trigger diferido de PostgreSQL rechaza toda transacción
    con `sum(debits) != sum(credits)`.
    """

    class Meta:
        model = LedgerEntry

    ledger_transaction = factory.SubFactory(LedgerTransactionFactory)
    account = factory.SubFactory(AccountFactory)
    direction = LedgerEntry.Direction.DEBIT
    amount = Decimal('10.00')
    currency = Account.Currency.ARS

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        with transaction.atomic():
            entry = super()._create(model_class, *args, **kwargs)
            cls._create_counterpart(entry)
        return entry

    @classmethod
    def _create_counterpart(cls, entry):
        """Crea el asiento contrario que equilibra la transacción."""
        opposite = (
            LedgerEntry.Direction.CREDIT
            if entry.direction == LedgerEntry.Direction.DEBIT
            else LedgerEntry.Direction.DEBIT
        )
        return LedgerEntry.objects.create(
            ledger_transaction=entry.ledger_transaction,
            account=AccountFactory(),
            direction=opposite,
            amount=entry.amount,
            currency=entry.currency,
        )
