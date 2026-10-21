"""Tests de concurrencia de loans contra PostgreSQL real."""

import threading
from decimal import Decimal

import pytest
from django.db import connections

from apps.loans.tests.factories import create_approved_user

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


def fund_user(user_id, amount='10000.00', key='fund'):
    """Deposita fondos simulados en la billetera del usuario."""
    from apps.ledger.services import deposit

    return deposit(
        user_id=user_id,
        currency='ARS',
        amount=Decimal(amount),
        idempotency_key=key,
    )


def make_offer(lender_user_id, amount='10000.00'):
    """Crea una oferta activa del prestamista."""
    from apps.offers.services import create_offer

    return create_offer(
        lender_user_id=lender_user_id,
        amount=Decimal(amount),
        currency='ARS',
        interest_rate=Decimal('24.00'),
        term_months=12,
    )


def test_two_borrowers_cannot_accept_the_same_offer():
    """Dos prestatarios concurrentes no pueden aceptar la misma oferta."""
    from apps.loans.models import Loan
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='conc-prestamista@example.com')
    first_borrower = create_approved_user(email='conc-prestatario-1@example.com')
    second_borrower = create_approved_user(email='conc-prestatario-2@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-conc')

    def worker(index):
        borrower = first_borrower if index == 0 else second_borrower
        return accept_offer(
            borrower_user_id=borrower.id,
            offer_id=offer.id,
            idempotency_key=f'conc-accept-{index}',
        ).id

    outcomes = run_in_parallel(worker)

    successful = [outcome for outcome in outcomes if not isinstance(outcome, Exception)]
    assert len(successful) == 1
    assert Loan.objects.count() == 1
    offer.refresh_from_db()
    assert offer.status == 'accepted'


def test_only_one_installment_can_be_paid_concurrently():
    """Dos pagos concurrentes de la misma cuota: solo uno se concreta."""
    from apps.loans.services import accept_offer, pay_installment

    lender = create_approved_user(email='conc-pago-prestamista@example.com')
    borrower = create_approved_user(email='conc-pago-prestatario@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-conc-pago')
    fund_user(borrower.id, amount='1000.00', key='fund-conc-pago-borrower')
    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='conc-pago-accept',
    )

    def worker(index):
        return pay_installment(
            loan_id=loan.id,
            number=1,
            borrower_user_id=borrower.id,
        ).id

    outcomes = run_in_parallel(worker)

    successful = [outcome for outcome in outcomes if not isinstance(outcome, Exception)]
    assert len(successful) == 1
    installment = loan.installments.get(number=1)
    assert installment.status == 'paid'


def test_concurrent_acceptance_is_idempotent_for_the_same_borrower():
    """El mismo prestatario con la misma clave concurrente obtiene un solo préstamo."""
    from apps.loans.models import Loan
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='conc-idem-prestamista@example.com')
    borrower = create_approved_user(email='conc-idem-prestatario@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-conc-idem')

    def worker(index):
        return accept_offer(
            borrower_user_id=borrower.id,
            offer_id=offer.id,
            idempotency_key='conc-idem',
        ).id

    outcomes = run_in_parallel(worker)

    successful = [outcome for outcome in outcomes if not isinstance(outcome, Exception)]
    assert len(successful) == 1
    assert Loan.objects.count() == 1
    assert Loan.objects.get().installments.count() == 12
