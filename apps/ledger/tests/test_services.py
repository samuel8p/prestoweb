"""Tests de los servicios de escritura del ledger."""

import uuid
from decimal import Decimal

import pytest

from apps.ledger.tests.factories import (
    AccountFactory,
    create_approved_user,
    create_identity_user,
)

pytestmark = pytest.mark.django_db


def test_create_user_wallet_creates_account():
    """Crear la billetera del usuario devuelve una cuenta en cero."""
    from apps.ledger.models import Account
    from apps.ledger.services import create_user_wallet

    user_id = uuid.uuid4()

    account = create_user_wallet(user_id=user_id, currency=Account.Currency.ARS)

    assert account.kind == Account.Kind.USER_WALLET
    assert account.user_id == user_id
    assert account.balance == Decimal('0.00')


def test_create_user_wallet_is_idempotent():
    """Pedir dos veces la misma billetera devuelve la misma cuenta."""
    from apps.ledger.models import Account
    from apps.ledger.services import create_user_wallet

    user_id = uuid.uuid4()

    first = create_user_wallet(user_id=user_id, currency=Account.Currency.ARS)
    second = create_user_wallet(user_id=user_id, currency=Account.Currency.ARS)

    assert first.id == second.id


def test_deposit_credits_wallet_and_debits_custody():
    """El depósito acredita la billetera y debita la cuenta de custodia."""
    from apps.ledger.models import Account
    from apps.ledger.services import deposit

    user = create_approved_user()
    wallet = AccountFactory(
        user_id=user.id,
        currency=Account.Currency.ARS,
        kind=Account.Kind.USER_WALLET,
        balance=Decimal('0.00'),
    )

    ledger_transaction = deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='dep-1',
    )

    wallet.refresh_from_db()
    assert ledger_transaction.type == 'deposit'
    assert wallet.balance == Decimal('100.00')


def test_deposit_requires_approved_kyc():
    """Sin KYC aprobada no se puede depositar."""
    from apps.core.exceptions import KYCNotCompleted
    from apps.ledger.models import Account
    from apps.ledger.services import deposit

    user = create_identity_user()

    with pytest.raises(KYCNotCompleted):
        deposit(
            user_id=user.id,
            currency=Account.Currency.ARS,
            amount=Decimal('100.00'),
            idempotency_key='dep-kyc',
        )


def test_deposit_rejects_non_positive_amount():
    """Un importe no positivo se rechaza."""
    from apps.core.exceptions import InvalidAmount
    from apps.ledger.models import Account
    from apps.ledger.services import deposit

    user = create_approved_user()

    with pytest.raises(InvalidAmount):
        deposit(
            user_id=user.id,
            currency=Account.Currency.ARS,
            amount=Decimal('0.00'),
            idempotency_key='dep-cero',
        )


def test_deposit_fails_when_simulated_deposits_disabled(settings):
    """Con los depósitos simulados deshabilitados la operación falla."""
    from apps.ledger.exceptions import SimulatedDepositsDisabled
    from apps.ledger.models import Account
    from apps.ledger.services import deposit

    settings.LEDGER_SIMULATED_DEPOSITS_ENABLED = False
    user = create_approved_user()

    with pytest.raises(SimulatedDepositsDisabled):
        deposit(
            user_id=user.id,
            currency=Account.Currency.ARS,
            amount=Decimal('100.00'),
            idempotency_key='dep-off',
        )


def test_withdraw_fails_when_simulated_deposits_disabled(settings):
    """Con los depósitos simulados deshabilitados el retiro también falla."""
    from apps.ledger.exceptions import SimulatedDepositsDisabled
    from apps.ledger.models import Account
    from apps.ledger.services import withdraw

    settings.LEDGER_SIMULATED_DEPOSITS_ENABLED = False
    user = create_approved_user()

    with pytest.raises(SimulatedDepositsDisabled):
        withdraw(
            user_id=user.id,
            currency=Account.Currency.ARS,
            amount=Decimal('10.00'),
            idempotency_key='ret-off',
        )


def test_deposit_same_idempotency_key_returns_original():
    """Misma clave de idempotencia y mismo payload devuelven la operación original."""
    from apps.ledger.models import Account
    from apps.ledger.services import deposit

    user = create_approved_user()

    first = deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='dep-idem',
    )
    second = deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='dep-idem',
    )

    assert first.id == second.id
    wallet = Account.objects.get(user_id=user.id, kind=Account.Kind.USER_WALLET)
    assert wallet.balance == Decimal('100.00')


def test_deposit_same_key_different_payload_raises_conflict():
    """Misma clave de idempotencia con payload distinto es un conflicto."""
    from apps.ledger.exceptions import IdempotencyConflict
    from apps.ledger.models import Account
    from apps.ledger.services import deposit

    user = create_approved_user()

    deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='dep-conflict',
    )

    with pytest.raises(IdempotencyConflict):
        deposit(
            user_id=user.id,
            currency=Account.Currency.ARS,
            amount=Decimal('250.00'),
            idempotency_key='dep-conflict',
        )


def test_withdraw_debits_wallet_and_credits_custody():
    """El retiro debita la billetera y acredita la cuenta de custodia."""
    from apps.ledger.models import Account
    from apps.ledger.services import deposit, withdraw

    user = create_approved_user()
    deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='dep-w',
    )

    withdraw(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('40.00'),
        idempotency_key='ret-1',
    )

    wallet = Account.objects.get(user_id=user.id, kind=Account.Kind.USER_WALLET)
    assert wallet.balance == Decimal('60.00')


def test_withdraw_without_funds_raises_insufficient_funds():
    """No se puede retirar más de lo que hay en la billetera."""
    from apps.core.exceptions import InsufficientFunds
    from apps.ledger.models import Account
    from apps.ledger.services import deposit, withdraw

    user = create_approved_user()
    deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='dep-i',
    )

    with pytest.raises(InsufficientFunds):
        withdraw(
            user_id=user.id,
            currency=Account.Currency.ARS,
            amount=Decimal('500.00'),
            idempotency_key='ret-i',
        )


def test_transfer_moves_balance_between_wallets():
    """La transferencia mueve saldo entre dos billeteras de la misma moneda."""
    from apps.ledger.models import Account
    from apps.ledger.services import create_user_wallet, deposit, transfer

    user = create_approved_user()
    other = create_approved_user(email='destinatario@example.com')
    deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='dep-t',
    )
    source = Account.objects.get(user_id=user.id, kind=Account.Kind.USER_WALLET)
    destination = create_user_wallet(user_id=other.id, currency=Account.Currency.ARS)

    transfer(
        user_id=user.id,
        source_account_id=source.id,
        destination_account_id=destination.id,
        amount=Decimal('30.00'),
        idempotency_key='tra-1',
    )

    source.refresh_from_db()
    destination.refresh_from_db()
    assert source.balance == Decimal('70.00')
    assert destination.balance == Decimal('30.00')


def test_transfer_rejects_same_account():
    """Una transferencia a la misma cuenta se rechaza."""
    from apps.ledger.exceptions import SameAccountTransfer
    from apps.ledger.models import Account
    from apps.ledger.services import create_user_wallet, transfer

    user = create_approved_user()
    account = create_user_wallet(user_id=user.id, currency=Account.Currency.ARS)

    with pytest.raises(SameAccountTransfer):
        transfer(
            user_id=user.id,
            source_account_id=account.id,
            destination_account_id=account.id,
            amount=Decimal('10.00'),
            idempotency_key='tra-misma',
        )


def test_transfer_rejects_different_currency():
    """Una transferencia entre monedas distintas se rechaza."""
    from apps.ledger.exceptions import CurrencyMismatch
    from apps.ledger.models import Account
    from apps.ledger.services import create_user_wallet, transfer

    user = create_approved_user()
    source = create_user_wallet(user_id=user.id, currency=Account.Currency.ARS)
    destination = create_user_wallet(user_id=uuid.uuid4(), currency=Account.Currency.USD)

    with pytest.raises(CurrencyMismatch):
        transfer(
            user_id=user.id,
            source_account_id=source.id,
            destination_account_id=destination.id,
            amount=Decimal('10.00'),
            idempotency_key='tra-moneda',
        )


def test_transfer_rejects_non_wallet_destination():
    """El destino de una transferencia debe ser una user_wallet."""
    from apps.ledger.exceptions import AccountKindNotAllowed
    from apps.ledger.models import Account
    from apps.ledger.services import create_user_wallet, transfer

    user = create_approved_user()
    source = create_user_wallet(user_id=user.id, currency=Account.Currency.ARS)
    destination = AccountFactory(
        user_id=None,
        currency=Account.Currency.ARS,
        kind=Account.Kind.CUSTODY,
        balance=Decimal('0.00'),
    )

    with pytest.raises(AccountKindNotAllowed):
        transfer(
            user_id=user.id,
            source_account_id=source.id,
            destination_account_id=destination.id,
            amount=Decimal('10.00'),
            idempotency_key='tra-kind',
        )


def test_transfer_rejects_other_user_source_account():
    """No se puede transferir desde la cuenta de otro usuario."""
    from apps.ledger.exceptions import AccountNotFound
    from apps.ledger.models import Account
    from apps.ledger.services import create_user_wallet, transfer

    user = create_approved_user()
    other = create_approved_user(email='tercero@example.com')
    source = create_user_wallet(user_id=other.id, currency=Account.Currency.ARS)
    destination = create_user_wallet(user_id=user.id, currency=Account.Currency.ARS)

    with pytest.raises(AccountNotFound):
        transfer(
            user_id=user.id,
            source_account_id=source.id,
            destination_account_id=destination.id,
            amount=Decimal('10.00'),
            idempotency_key='tra-ajeno',
        )


def test_balance_matches_entries_invariant():
    """El saldo de cada cuenta es igual a creditos - debitos de sus asientos."""
    from apps.ledger.models import Account, LedgerEntry
    from apps.ledger.services import deposit, withdraw

    user = create_approved_user()
    deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='inv-dep',
    )
    withdraw(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('25.00'),
        idempotency_key='inv-ret',
    )

    for account in Account.objects.all():
        entries = LedgerEntry.objects.filter(account=account)
        credits = sum(
            (entry.amount for entry in entries if entry.direction == 'credit'),
            Decimal('0.00'),
        )
        debits = sum(
            (entry.amount for entry in entries if entry.direction == 'debit'),
            Decimal('0.00'),
        )
        assert account.balance == credits - debits


def test_custody_balance_is_the_negative_sum_of_user_wallets():
    """En cada moneda, la custodia es exactamente la suma negativa de las billeteras."""
    from apps.ledger.models import Account
    from apps.ledger.services import create_user_wallet, deposit, transfer, withdraw

    first = create_approved_user()
    second = create_approved_user(email='invariante@example.com')
    deposit(
        user_id=first.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='inv-c-dep-1',
    )
    deposit(
        user_id=second.id,
        currency=Account.Currency.ARS,
        amount=Decimal('250.00'),
        idempotency_key='inv-c-dep-2',
    )
    deposit(
        user_id=first.id,
        currency=Account.Currency.USD,
        amount=Decimal('80.00'),
        idempotency_key='inv-c-dep-3',
    )
    withdraw(
        user_id=second.id,
        currency=Account.Currency.ARS,
        amount=Decimal('50.00'),
        idempotency_key='inv-c-ret',
    )
    source = Account.objects.get(
        user_id=first.id,
        kind=Account.Kind.USER_WALLET,
        currency=Account.Currency.ARS,
    )
    destination = create_user_wallet(user_id=second.id, currency=Account.Currency.ARS)
    transfer(
        user_id=first.id,
        source_account_id=source.id,
        destination_account_id=destination.id,
        amount=Decimal('30.00'),
        idempotency_key='inv-c-tra',
    )

    for currency in (Account.Currency.ARS, Account.Currency.USD):
        wallets_total = sum(
            Account.objects.filter(
                kind=Account.Kind.USER_WALLET,
                currency=currency,
            ).values_list('balance', flat=True),
            Decimal('0.00'),
        )
        custody = Account.objects.filter(
            kind=Account.Kind.CUSTODY,
            currency=currency,
        ).first()
        custody_balance = custody.balance if custody else Decimal('0.00')
        assert custody_balance == -wallets_total


def test_reverse_creates_compensating_transaction():
    """El reverso crea una transacción compensatoria con los importes invertidos."""
    from apps.ledger.models import Account
    from apps.ledger.services import deposit, reverse_transaction

    user = create_approved_user()
    original = deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='rev-dep',
    )

    reversal = reverse_transaction(
        transaction_id=original.id,
        staff_user_id=uuid.uuid4(),
    )

    assert reversal.type == 'reversal'
    assert reversal.reverses_id == original.id
    wallet = Account.objects.get(user_id=user.id, kind=Account.Kind.USER_WALLET)
    assert wallet.balance == Decimal('0.00')


def test_reverse_fails_when_wallet_would_go_negative():
    """El reverso falla si dejaría la billetera en negativo."""
    from apps.core.exceptions import InsufficientFunds
    from apps.ledger.models import Account
    from apps.ledger.services import deposit, reverse_transaction, withdraw

    user = create_approved_user()
    original = deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='rev-neg',
    )
    withdraw(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='rev-neg-ret',
    )

    with pytest.raises(InsufficientFunds):
        reverse_transaction(
            transaction_id=original.id,
            staff_user_id=uuid.uuid4(),
        )


def test_reverse_is_only_allowed_once():
    """Una transacción no puede reversarse dos veces."""
    from apps.ledger.exceptions import LedgerError
    from apps.ledger.models import Account
    from apps.ledger.services import deposit, reverse_transaction

    user = create_approved_user()
    original = deposit(
        user_id=user.id,
        currency=Account.Currency.ARS,
        amount=Decimal('100.00'),
        idempotency_key='rev-once',
    )
    reverse_transaction(transaction_id=original.id, staff_user_id=uuid.uuid4())

    with pytest.raises(LedgerError):
        reverse_transaction(transaction_id=original.id, staff_user_id=uuid.uuid4())
