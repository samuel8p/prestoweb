"""Tests de concurrencia de los servicios de offers."""

import threading
import time
from decimal import Decimal

import pytest

from apps.offers.tests.factories import create_approved_user

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

    threads = [
        threading.Thread(target=run, args=(index,), name=f'offer-update-{index}')
        for index in range(workers)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return outcomes


def test_concurrent_offer_updates_do_not_lose_changes(monkeypatch):
    """Dos actualizaciones simultáneas de la misma oferta no se pisan entre sí."""
    from apps.offers.models import Offer
    from apps.offers.services import update_offer

    original_save = Offer.save
    save_barrier = threading.Barrier(2, timeout=2)

    def save_after_both_read(self, *args, **kwargs):
        try:
            save_barrier.wait()
        except threading.BrokenBarrierError:
            pass
        # El primer hilo escribe después del segundo: si leyó una versión
        # vieja, pisa el cambio del otro.
        if threading.current_thread().name == 'offer-update-0':
            time.sleep(0.2)
        return original_save(self, *args, **kwargs)

    monkeypatch.setattr(Offer, 'save', save_after_both_read)

    lender = create_approved_user(email='concurrencia-oferta@example.com')
    offer = _create_offer(lender)

    def worker(index):
        if index == 0:
            return update_offer(
                offer_id=offer.id,
                lender_user_id=lender.id,
                amount=Decimal('20000.00'),
            )
        return update_offer(
            offer_id=offer.id,
            lender_user_id=lender.id,
            requirements='requisitos nuevos',
        )

    run_in_parallel(worker)

    offer.refresh_from_db()
    assert offer.amount == Decimal('20000.00')
    assert offer.requirements == 'requisitos nuevos'


def _create_offer(lender):
    """Crea una oferta activa para el prestamista."""
    from apps.offers.services import create_offer

    return create_offer(
        lender_user_id=lender.id,
        amount=Decimal('10000.00'),
        currency='ARS',
        interest_rate=Decimal('24.00'),
        term_months=12,
    )
