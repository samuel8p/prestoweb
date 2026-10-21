"""Tests de concurrencia del ledger contra PostgreSQL real.

Las pruebas usan `transaction=True` (sin wrapping atómico) y hilos reales con
conexiones propias, que es el único escenario donde `select_for_update()`
puede demostrar que no hay lost updates ni saldos negativos.
"""

import threading
from decimal import Decimal

import pytest
from django.db import connections

from apps.ledger.tests.factories import create_approved_user

pytestmark = pytest.mark.django_db(transaction=True)


def run_in_parallel(worker, workers=2):
    """Ejecuta `worker(index)` en varios hilos sincronizados por una barrera."""
    barrier = threading.Barrier(workers)
    outcomes = []

    def run(index):
        barrier.wait()
        try:
            outcomes.append(worker(index))
        except Exception as exc:  # noqa: BLE001 - se re-lanza en el hilo principal
            outcomes.append(exc)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=run, args=(index,)) for index in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return outcomes


def test_concurrent_deposits_with_same_key_create_one_transaction():
    """Dos depósitos concurrentes con la misma clave dejan una sola transacción."""
    from apps.ledger.models import LedgerTransaction
    from apps.ledger.services import deposit

    user = create_approved_user()

    def worker(index):
        return deposit(
            user_id=user.id,
            currency='ARS',
            amount=Decimal('50.00'),
            idempotency_key='conc-dep-1',
        ).id

    outcomes = run_in_parallel(worker)

    assert not any(isinstance(outcome, Exception) for outcome in outcomes), outcomes
    assert len(set(outcomes)) == 1
    assert (
        LedgerTransaction.objects.filter(
            created_by_user_id=user.id,
            idempotency_key='conc-dep-1',
        ).count()
        == 1
    )


def test_concurrent_withdrawals_never_leave_a_negative_balance():
    """Dos retiros concurrentes nunca dejan la billetera en negativo."""
    from apps.core.exceptions import InsufficientFunds
    from apps.ledger.models import Account
    from apps.ledger.services import deposit, withdraw

    user = create_approved_user()
    deposit(
        user_id=user.id,
        currency='ARS',
        amount=Decimal('100.00'),
        idempotency_key='conc-dep-2',
    )

    def worker(index):
        return withdraw(
            user_id=user.id,
            currency='ARS',
            amount=Decimal('80.00'),
            idempotency_key=f'conc-ret-{index}',
        ).id

    outcomes = run_in_parallel(worker)

    wallet = Account.objects.get(user_id=user.id, kind=Account.Kind.USER_WALLET)
    successful = [outcome for outcome in outcomes if not isinstance(outcome, Exception)]
    rejected = [outcome for outcome in outcomes if isinstance(outcome, InsufficientFunds)]
    assert len(successful) == 1
    assert len(rejected) == 1
    assert wallet.balance == Decimal('20.00')
    assert wallet.balance >= Decimal('0.00')


def test_concurrent_transfers_conserve_the_total_balance():
    """Dos transferencias concurrentes no pierden saldo: la suma se conserva."""
    from apps.ledger.models import Account
    from apps.ledger.services import deposit, transfer

    sender = create_approved_user()
    receiver = create_approved_user(email='conc-receptor@example.com')
    deposit(
        user_id=sender.id,
        currency='ARS',
        amount=Decimal('100.00'),
        idempotency_key='conc-dep-3',
    )
    deposit(
        user_id=receiver.id,
        currency='ARS',
        amount=Decimal('100.00'),
        idempotency_key='conc-dep-4',
    )
    source = Account.objects.get(user_id=sender.id, kind=Account.Kind.USER_WALLET)
    destination = Account.objects.get(user_id=receiver.id, kind=Account.Kind.USER_WALLET)

    def worker(index):
        return transfer(
            user_id=sender.id,
            source_account_id=source.id,
            destination_account_id=destination.id,
            amount=Decimal('30.00'),
            idempotency_key=f'conc-tra-{index}',
        ).id

    outcomes = run_in_parallel(worker)

    source.refresh_from_db()
    destination.refresh_from_db()
    assert not any(isinstance(outcome, Exception) for outcome in outcomes), outcomes
    assert source.balance == Decimal('40.00')
    assert destination.balance == Decimal('160.00')
    assert source.balance + destination.balance == Decimal('200.00')


def test_concurrent_deposits_keep_the_balance_invariant():
    """Después de depósitos concurrentes el saldo sigue creditos - debitos."""
    from apps.ledger.models import Account, LedgerEntry
    from apps.ledger.services import deposit

    user = create_approved_user()

    def worker(index):
        return deposit(
            user_id=user.id,
            currency='ARS',
            amount=Decimal('10.00'),
            idempotency_key=f'conc-dep-5-{index}',
        ).id

    run_in_parallel(worker)

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
