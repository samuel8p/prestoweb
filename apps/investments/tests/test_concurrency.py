"""Tests de concurrencia e invariantes de investments contra PostgreSQL real."""

import threading
from datetime import date
from decimal import Decimal

import pytest
from django.db import connections

from apps.investments.tests.factories import (
    InvestmentProductFactory,
    create_approved_user,
    fund_user,
)

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


def test_two_concurrent_openings_with_the_same_key_create_one_position():
    """Dos aperturas concurrentes con la misma clave dejan una sola posición."""
    from apps.investments.models import Position
    from apps.investments.services import open_position

    user = create_approved_user()
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='conc-inv-dep')

    def worker(index):
        return open_position(
            user_id=user.id,
            product_id=product.id,
            amount=Decimal('5000.00'),
            idempotency_key='conc-inv-open',
        ).id

    outcomes = run_in_parallel(worker)

    successful = [outcome for outcome in outcomes if not isinstance(outcome, Exception)]
    assert len(successful) == 2
    assert len(set(successful)) == 1
    assert Position.objects.count() == 1


def test_concurrent_settlement_pays_the_position_only_once():
    """Dos liquidaciones concurrentes pagan la posición una sola vez."""
    from apps.investments.services import open_position, settle_matured_positions
    from apps.ledger.selectors import get_user_wallet

    user = create_approved_user()
    product = InvestmentProductFactory(
        term_days=30,
        annual_rate_tna=Decimal('12.00'),
        min_amount=Decimal('1000.00'),
    )
    fund_user(user.id, amount='10000.00', key='conc-settle-dep')
    open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='conc-settle-open',
    )

    def worker(index):
        return settle_matured_positions(today=date(2030, 1, 1))

    run_in_parallel(worker)

    wallet = get_user_wallet(user_id=user.id, currency='ARS')
    assert wallet.balance == Decimal('10049.32')


def test_ledger_invariant_holds_with_investments():
    """Con inversiones, las cuentas de contrapartida igualan a las billeteras."""
    from apps.investments.services import open_position
    from apps.ledger.selectors import get_balance_breakdown

    user = create_approved_user()
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='inv-dep')

    open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='inv-invariant',
    )

    breakdown = get_balance_breakdown(currency='ARS')

    assert breakdown['custody'] + breakdown['system'] == -breakdown['user_wallet']


def test_ledger_total_balance_is_zero_with_investments():
    """La suma de todos los saldos por moneda es cero."""
    from apps.investments.services import open_position
    from apps.ledger.selectors import get_balance_breakdown

    user = create_approved_user()
    product = InvestmentProductFactory(min_amount=Decimal('1000.00'))
    fund_user(user.id, amount='10000.00', key='inv-dep-2')

    open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='inv-total',
    )

    breakdown = get_balance_breakdown(currency='ARS')

    assert breakdown['total'] == Decimal('0.00')
