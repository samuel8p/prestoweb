"""Tests de los triggers de PostgreSQL del ledger.

- Constraint trigger diferido: `sum(debits) = sum(credits)` por transacción.
- Triggers de inmutabilidad: `LedgerTransaction` y `LedgerEntry` no admiten
  `UPDATE` ni `DELETE`.
"""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.ledger.tests.factories import (
    AccountFactory,
    LedgerEntryFactory,
    LedgerTransactionFactory,
)

pytestmark = pytest.mark.django_db(transaction=True)


def test_balanced_transaction_is_accepted():
    """Una transacción con un débito y un crédito del mismo importe se acepta."""
    from apps.ledger.models import LedgerEntry

    account = AccountFactory()
    other_account = AccountFactory()
    ledger_transaction = LedgerTransactionFactory()

    with transaction.atomic():
        LedgerEntry.objects.create(
            ledger_transaction=ledger_transaction,
            account=account,
            direction=LedgerEntry.Direction.DEBIT,
            amount=Decimal('10.00'),
            currency='ARS',
        )
        LedgerEntry.objects.create(
            ledger_transaction=ledger_transaction,
            account=other_account,
            direction=LedgerEntry.Direction.CREDIT,
            amount=Decimal('10.00'),
            currency='ARS',
        )

    assert ledger_transaction.entries.count() == 2


def test_unbalanced_transaction_is_rejected():
    """Una transacción con un solo débito es rechazada por el trigger diferido."""
    from apps.ledger.models import LedgerEntry

    account = AccountFactory()
    ledger_transaction = LedgerTransactionFactory()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LedgerEntry.objects.create(
                ledger_transaction=ledger_transaction,
                account=account,
                direction=LedgerEntry.Direction.DEBIT,
                amount=Decimal('10.00'),
                currency='ARS',
            )


def test_transaction_with_different_amounts_is_rejected():
    """Débitos y créditos con importes distintos también se rechazan."""
    from apps.ledger.models import LedgerEntry

    account = AccountFactory()
    other_account = AccountFactory()
    ledger_transaction = LedgerTransactionFactory()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LedgerEntry.objects.create(
                ledger_transaction=ledger_transaction,
                account=account,
                direction=LedgerEntry.Direction.DEBIT,
                amount=Decimal('10.00'),
                currency='ARS',
            )
            LedgerEntry.objects.create(
                ledger_transaction=ledger_transaction,
                account=other_account,
                direction=LedgerEntry.Direction.CREDIT,
                amount=Decimal('7.50'),
                currency='ARS',
            )


def test_ledger_transaction_cannot_be_updated():
    """Una transacción del libro mayor es inmutable."""
    ledger_transaction = LedgerTransactionFactory()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ledger_transaction.description = 'descripcion modificada'
            ledger_transaction.save()


def test_ledger_transaction_cannot_be_deleted():
    """Una transacción del libro mayor no se puede borrar."""
    ledger_transaction = LedgerTransactionFactory()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ledger_transaction.delete()


def test_ledger_entry_cannot_be_updated():
    """Un asiento es inmutable."""
    entry = LedgerEntryFactory()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            entry.amount = Decimal('999.00')
            entry.save()


def test_ledger_entry_cannot_be_deleted():
    """Un asiento no se puede borrar."""
    entry = LedgerEntryFactory()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            entry.delete()
