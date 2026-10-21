"""Tests de concurrencia de la categorización de gastos."""

import threading
from decimal import Decimal

import pytest

from apps.budgets.tests.factories import create_approved_user

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
            from django.db import connections

            connections.close_all()

    threads = [threading.Thread(target=run, args=(index,)) for index in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return outcomes


def test_concurrent_categorization_of_the_same_movement_creates_one_expense():
    """Dos categorizaciones simultáneas del mismo movimiento dejan un solo gasto."""
    from apps.budgets.models import Expense
    from apps.budgets.services import categorize_movement, create_category
    from apps.ledger.services import deposit, withdraw

    user = create_approved_user(email='concurrencia-categoria@example.com')
    category = create_category(user_id=user.id, name='Comida')
    deposit(
        user_id=user.id,
        currency='ARS',
        amount=Decimal('1000.00'),
        idempotency_key='concurrencia-fondo',
    )
    movement = withdraw(
        user_id=user.id,
        currency='ARS',
        amount=Decimal('100.00'),
        idempotency_key='concurrencia-gasto',
    )

    def worker(index):
        return categorize_movement(
            user_id=user.id,
            ledger_transaction_id=movement.id,
            category_id=category.id,
        )

    outcomes = run_in_parallel(worker)

    assert len(Expense.objects.filter(user_id=user.id)) == 1
    created = [outcome for outcome in outcomes if not isinstance(outcome, Exception)]
    failed = [outcome for outcome in outcomes if isinstance(outcome, Exception)]
    assert len(created) == 1
    assert failed, 'la segunda categorización concurrente debería fallar'
