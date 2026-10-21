"""Tests de los servicios de escritura de loans."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.loans.tests.factories import LoanFactory, create_approved_user

pytestmark = pytest.mark.django_db


def fund_user(user_id, amount='10000.00', currency='ARS', key='fund'):
    """Deposita fondos simulados en la billetera del usuario."""
    from apps.ledger.services import deposit

    return deposit(
        user_id=user_id,
        currency=currency,
        amount=Decimal(amount),
        idempotency_key=key,
    )


def make_offer(lender_user_id, amount='10000.00', rate='24.00', months=12, currency='ARS'):
    """Crea una oferta activa del prestamista."""
    from apps.offers.services import create_offer

    return create_offer(
        lender_user_id=lender_user_id,
        amount=Decimal(amount),
        currency=currency,
        interest_rate=Decimal(rate),
        term_months=months,
    )


def test_accept_offer_creates_active_loan(client_placeholder=None):
    """Aceptar una oferta crea el préstamo activo del prestatario."""
    from apps.loans.models import Loan
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='prestamista-accept@example.com')
    borrower = create_approved_user(email='prestatario-accept@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-accept')

    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-1',
    )

    assert loan.status == Loan.Status.ACTIVE
    assert loan.borrower_user_id == borrower.id
    assert loan.lender_user_id == lender.id
    assert loan.principal == Decimal('10000.00')
    assert loan.installments.count() == 12


def test_accept_offer_creates_immutable_snapshot():
    """Aceptar una oferta guarda el snapshot inmutable de los términos."""
    from apps.loans.models import OfferTermsSnapshot
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='prestamista-snap@example.com')
    borrower = create_approved_user(email='prestatario-snap@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-snap')

    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-snap',
    )

    snapshot = OfferTermsSnapshot.objects.get(loan=loan)
    assert snapshot.is_immutable is True
    assert snapshot.accepted_by_user_id == borrower.id
    assert snapshot.snapshot_data['interest_rate'] == '24.00'
    assert snapshot.snapshot_data['term_months'] == 12


def test_accept_offer_disburses_to_borrower():
    """Aceptar una oferta desembolsa el capital al prestatario."""
    from apps.ledger.selectors import get_user_wallet
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='prestamista-pago@example.com')
    borrower = create_approved_user(email='prestatario-pago@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-pago')

    accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-pago',
    )

    lender_wallet = get_user_wallet(user_id=lender.id, currency='ARS')
    borrower_wallet = get_user_wallet(user_id=borrower.id, currency='ARS')
    assert lender_wallet.balance == Decimal('0.00')
    assert borrower_wallet.balance == Decimal('10000.00')


def test_accept_offer_requires_approved_kyc():
    """Sin KYC aprobada no se puede aceptar una oferta."""
    from apps.core.exceptions import KYCNotCompleted
    from apps.identity.services import register_user
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='prestamista-kyc@example.com')
    borrower = register_user(email='prestatario-kyc@example.com', password='TestPass123!')
    offer = make_offer(lender.id)

    with pytest.raises(KYCNotCompleted):
        accept_offer(
            borrower_user_id=borrower.id,
            offer_id=offer.id,
            idempotency_key='accept-kyc',
        )


def test_accept_offer_rejects_own_offer():
    """El prestamista no puede aceptar su propia oferta."""
    from apps.loans.services import accept_offer
    from apps.offers.exceptions import CannotAcceptOwnOffer

    lender = create_approved_user(email='prestamista-propia@example.com')
    offer = make_offer(lender.id)

    with pytest.raises(CannotAcceptOwnOffer):
        accept_offer(
            borrower_user_id=lender.id,
            offer_id=offer.id,
            idempotency_key='accept-propia',
        )


def test_accept_offer_rejects_inactive_offer():
    """Una oferta expirada no se puede aceptar."""
    from apps.loans.services import accept_offer
    from apps.offers.exceptions import OfferNotAcceptable
    from apps.offers.services import expire_offer

    lender = create_approved_user(email='prestamista-expired@example.com')
    borrower = create_approved_user(email='prestatario-expired@example.com')
    offer = make_offer(lender.id)
    expire_offer(offer_id=offer.id, lender_user_id=lender.id)

    with pytest.raises(OfferNotAcceptable):
        accept_offer(
            borrower_user_id=borrower.id,
            offer_id=offer.id,
            idempotency_key='accept-expired',
        )


def test_accept_offer_is_idempotent():
    """La misma clave de idempotencia devuelve el préstamo original."""
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='prestamista-idem@example.com')
    borrower = create_approved_user(email='prestatario-idem@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-idem')

    first = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-idem',
    )
    second = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-idem',
    )

    assert first.id == second.id
    assert first.installments.count() == 12


def test_accept_offer_same_key_different_offer_raises_conflict():
    """La misma clave con otra oferta devuelve conflicto."""
    from apps.ledger.exceptions import IdempotencyConflict
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='prestamista-conflict@example.com')
    borrower = create_approved_user(email='prestatario-conflict@example.com')
    first_offer = make_offer(lender.id, amount='10000.00')
    second_offer = make_offer(lender.id, amount='20000.00')
    fund_user(lender.id, amount='30000.00', key='fund-conflict')

    accept_offer(
        borrower_user_id=borrower.id,
        offer_id=first_offer.id,
        idempotency_key='accept-conflict',
    )

    with pytest.raises(IdempotencyConflict):
        accept_offer(
            borrower_user_id=borrower.id,
            offer_id=second_offer.id,
            idempotency_key='accept-conflict',
        )


def test_accept_offer_rolls_back_when_lender_has_no_funds():
    """Si el prestamista no tiene saldo, no queda préstamo ni oferta aceptada."""
    from apps.core.exceptions import InsufficientFunds
    from apps.loans.models import Loan
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='prestamista-sin-plata@example.com')
    borrower = create_approved_user(email='prestatario-sin-plata@example.com')
    offer = make_offer(lender.id)

    with pytest.raises(InsufficientFunds):
        accept_offer(
            borrower_user_id=borrower.id,
            offer_id=offer.id,
            idempotency_key='accept-sin-plata',
        )

    offer.refresh_from_db()
    assert offer.status == 'active'
    assert Loan.objects.count() == 0


def test_installment_principal_parts_sum_to_principal():
    """La suma de las partes de capital de las cuotas es el principal."""
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='prestamista-capital@example.com')
    borrower = create_approved_user(email='prestatario-capital@example.com')
    offer = make_offer(lender.id, amount='10000.00')
    fund_user(lender.id, key='fund-capital')

    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-capital',
    )

    principal_sum = sum(
        (installment.principal_amount for installment in loan.installments.all()),
        Decimal('0.00'),
    )
    assert principal_sum == loan.principal


def test_installment_amount_matches_french_installment():
    """El importe de las cuotas coincide con la cuota francesa calculada."""
    from apps.core.money import french_installment
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='prestamista-cuota@example.com')
    borrower = create_approved_user(email='prestatario-cuota@example.com')
    offer = make_offer(lender.id, amount='10000.00', rate='24.00', months=12)
    fund_user(lender.id, key='fund-cuota')

    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-cuota',
    )

    expected = french_installment(
        principal=Decimal('10000.00'),
        annual_tna=Decimal('24.00'),
        months=12,
    )
    installments = list(loan.installments.order_by('number'))
    assert installments[0].amount == expected
    assert installments[-1].amount == expected


def test_installments_have_consecutive_due_dates():
    """Las cuotas vencen una por mes desde la aceptación."""
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='prestamista-vence@example.com')
    borrower = create_approved_user(email='prestatario-vence@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-vence')

    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-vence',
    )

    installments = list(loan.installments.order_by('number'))
    assert installments[0].due_date > installments[0].due_date - timedelta(days=40)
    for previous, current in zip(installments, installments[1:], strict=False):
        assert current.due_date > previous.due_date


def test_pay_installment_moves_money_to_lender():
    """Pagar una cuota mueve el importe al prestamista."""
    from apps.ledger.selectors import get_user_wallet
    from apps.loans.services import accept_offer, pay_installment

    lender = create_approved_user(email='prestamista-cuota-pago@example.com')
    borrower = create_approved_user(email='prestatario-cuota-pago@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-cuota-pago')

    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-cuota-pago',
    )
    installment = loan.installments.order_by('number').first()

    paid = pay_installment(
        loan_id=loan.id,
        number=installment.number,
        borrower_user_id=borrower.id,
    )

    assert paid.status == 'paid'
    assert paid.paid_at is not None
    lender_wallet = get_user_wallet(user_id=lender.id, currency='ARS')
    borrower_wallet = get_user_wallet(user_id=borrower.id, currency='ARS')
    assert lender_wallet.balance == installment.amount
    assert borrower_wallet.balance == Decimal('10000.00') - installment.amount


def test_pay_installment_only_borrower_can_pay():
    """Solo el prestatario puede pagar las cuotas."""
    from apps.loans.exceptions import NotTheBorrower
    from apps.loans.services import accept_offer, pay_installment

    lender = create_approved_user(email='prestamista-no-paga@example.com')
    borrower = create_approved_user(email='prestatario-no-paga@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-no-paga')

    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-no-paga',
    )

    with pytest.raises(NotTheBorrower):
        pay_installment(
            loan_id=loan.id,
            number=1,
            borrower_user_id=lender.id,
        )


def test_pay_installment_requires_order():
    """Las cuotas se pagan en orden."""
    from apps.loans.exceptions import InstallmentOutOfOrder
    from apps.loans.services import accept_offer, pay_installment

    lender = create_approved_user(email='prestamista-orden@example.com')
    borrower = create_approved_user(email='prestatario-orden@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-orden')

    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-orden',
    )

    with pytest.raises(InstallmentOutOfOrder):
        pay_installment(
            loan_id=loan.id,
            number=2,
            borrower_user_id=borrower.id,
        )


def test_paying_every_installment_marks_loan_paid():
    """Al pagar todas las cuotas el préstamo pasa a paid."""
    from apps.loans.models import Loan
    from apps.loans.services import accept_offer, pay_installment

    lender = create_approved_user(email='prestamista-paid@example.com')
    borrower = create_approved_user(email='prestatario-paid@example.com')
    offer = make_offer(lender.id, amount='3000.00', months=3)
    fund_user(lender.id, amount='3000.00', key='fund-paid')
    fund_user(borrower.id, amount='1000.00', key='fund-paid-borrower')

    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-paid',
    )
    for number in range(1, 4):
        pay_installment(
            loan_id=loan.id,
            number=number,
            borrower_user_id=borrower.id,
        )

    loan.refresh_from_db()
    assert loan.status == Loan.Status.PAID


def test_mark_overdue_marks_installment_and_loan():
    """Las cuotas vencidas se marcan y el préstamo pasa a defaulted."""
    from apps.loans.models import Installment, Loan
    from apps.loans.services import accept_offer, mark_overdue

    lender = create_approved_user(email='prestamista-vencida@example.com')
    borrower = create_approved_user(email='prestatario-vencida@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-vencida')

    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-vencida',
    )

    count = mark_overdue(today=date(2030, 1, 1))

    loan.refresh_from_db()
    first = loan.installments.order_by('number').first()
    assert count == 12
    assert loan.status == Loan.Status.DEFAULTED
    assert first.status == Installment.Status.OVERDUE


def test_paying_overdue_installment_returns_loan_to_active():
    """Al pagar las cuotas vencidas el préstamo vuelve a active."""
    from apps.loans.models import Loan
    from apps.loans.services import accept_offer, mark_overdue, pay_installment

    lender = create_approved_user(email='prestamista-recupera@example.com')
    borrower = create_approved_user(email='prestatario-recupera@example.com')
    offer = make_offer(lender.id, amount='3000.00', months=3)
    fund_user(lender.id, amount='3000.00', key='fund-recupera')
    fund_user(borrower.id, amount='1000.00', key='fund-recupera-borrower')

    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-recupera',
    )
    mark_overdue(today=date(2030, 1, 1))

    for number in range(1, 4):
        pay_installment(
            loan_id=loan.id,
            number=number,
            borrower_user_id=borrower.id,
        )

    loan.refresh_from_db()
    assert loan.status == Loan.Status.PAID


def test_paying_overdue_installment_keeps_loan_in_default_until_all_are_paid():
    """Mientras queden cuotas vencidas el préstamo sigue en defaulted."""
    from apps.loans.models import Loan
    from apps.loans.services import accept_offer, mark_overdue, pay_installment

    lender = create_approved_user(email='prestamista-default@example.com')
    borrower = create_approved_user(email='prestatario-default@example.com')
    offer = make_offer(lender.id, amount='3000.00', months=3)
    fund_user(lender.id, amount='3000.00', key='fund-default')
    fund_user(borrower.id, amount='1000.00', key='fund-default-borrower')

    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-default',
    )
    mark_overdue(today=date(2030, 1, 1))

    pay_installment(loan_id=loan.id, number=1, borrower_user_id=borrower.id)

    loan.refresh_from_db()
    assert loan.status == Loan.Status.DEFAULTED


def test_invalid_state_transition_raises():
    """Un préstamo pagado no puede volver a active."""
    from apps.loans.exceptions import InvalidLoanTransition
    from apps.loans.models import Loan
    from apps.loans.services import accept_offer, change_loan_status, pay_installment

    lender = create_approved_user(email='prestamista-invalid@example.com')
    borrower = create_approved_user(email='prestatario-invalid@example.com')
    offer = make_offer(lender.id, amount='3000.00', months=2)
    fund_user(lender.id, amount='3000.00', key='fund-invalid')
    fund_user(borrower.id, amount='1000.00', key='fund-invalid-borrower')

    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-invalid',
    )
    for number in range(1, 3):
        pay_installment(loan_id=loan.id, number=number, borrower_user_id=borrower.id)

    loan.refresh_from_db()
    assert loan.status == Loan.Status.PAID

    with pytest.raises(InvalidLoanTransition):
        change_loan_status(loan_id=loan.id, new_status=Loan.Status.ACTIVE)


def test_valid_state_transition_is_applied():
    """Un préstamo activo puede pasar a defaulted."""
    from apps.loans.models import Loan
    from apps.loans.services import accept_offer, change_loan_status

    lender = create_approved_user(email='prestamista-transicion@example.com')
    borrower = create_approved_user(email='prestatario-transicion@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-transicion')

    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-transicion',
    )

    updated = change_loan_status(loan_id=loan.id, new_status=Loan.Status.DEFAULTED)

    assert updated.status == Loan.Status.DEFAULTED


def test_accept_offer_recovers_from_idempotency_integrity_error():
    """Ante un IntegrityError de concurrencia se devuelve el préstamo original."""
    from unittest.mock import patch

    from django.db import IntegrityError

    from apps.ledger.services import build_request_hash
    from apps.loans.models import Loan
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='recovery-prestamista@example.com')
    borrower = create_approved_user(email='recovery-prestatario@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-recovery')
    original = Loan.objects.create(
        borrower_user_id=borrower.id,
        lender_user_id=lender.id,
        offer_id=offer.id,
        principal=Decimal('10000.00'),
        currency='ARS',
        interest_rate=Decimal('24.00'),
        term_months=12,
        status=Loan.Status.ACTIVE,
        idempotency_key='recovery',
        request_hash=build_request_hash({'offer_id': str(offer.id)}),
    )
    calls = []

    def fake_resolve(user_id, idempotency_key, request_hash):
        calls.append(1)
        return None if len(calls) == 1 else original

    with (
        patch('apps.loans.services._resolve_idempotent', side_effect=fake_resolve),
        patch('apps.loans.services.Loan.objects.create', side_effect=IntegrityError),
    ):
        result = accept_offer(
            borrower_user_id=borrower.id,
            offer_id=offer.id,
            idempotency_key='recovery',
        )

    assert result.id == original.id


def test_pay_installment_of_unknown_loan_raises():
    """Pagar la cuota de un préstamo inexistente falla."""
    from apps.loans.exceptions import LoanNotFound
    from apps.loans.services import pay_installment

    borrower = create_approved_user(email='inexistente-prestatario@example.com')

    with pytest.raises(LoanNotFound):
        pay_installment(
            loan_id=uuid.uuid4(),
            number=1,
            borrower_user_id=borrower.id,
        )


def test_change_loan_status_of_unknown_loan_raises():
    """Cambiar el estado de un préstamo inexistente falla."""
    from apps.loans.exceptions import LoanNotFound
    from apps.loans.services import change_loan_status

    with pytest.raises(LoanNotFound):
        change_loan_status(loan_id=uuid.uuid4(), new_status='defaulted')


def test_list_installments_returns_ordered_installments():
    """El selector devuelve las cuotas ordenadas por número."""
    from apps.loans.selectors import list_installments
    from apps.loans.services import accept_offer

    lender = create_approved_user(email='orden-cuotas-prestamista@example.com')
    borrower = create_approved_user(email='orden-cuotas-prestatario@example.com')
    offer = make_offer(lender.id)
    fund_user(lender.id, key='fund-orden-cuotas')

    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='accept-orden-cuotas',
    )

    numbers = [installment.number for installment in list_installments(loan_id=loan.id)]

    assert numbers == list(range(1, 13))
