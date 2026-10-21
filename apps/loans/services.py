"""Servicios de escritura de la app loans (interfaz pública)."""

import calendar
import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.exceptions import KYCNotCompleted
from apps.core.money import french_installment, monthly_rate_from_annual_tna, round_two
from apps.identity.selectors import is_kyc_approved
from apps.ledger import services as ledger_services
from apps.ledger.exceptions import IdempotencyConflict
from apps.loans.exceptions import (
    InstallmentAlreadyPaid,
    InstallmentOutOfOrder,
    InvalidLoanTransition,
    LoanNotFound,
    NotTheBorrower,
)
from apps.loans.models import Installment, Loan, OfferTermsSnapshot
from apps.offers import services as offers_services

logger = logging.getLogger(__name__)

VALID_TRANSITIONS = {
    Loan.Status.ACTIVE: frozenset({Loan.Status.PAID, Loan.Status.DEFAULTED}),
    Loan.Status.DEFAULTED: frozenset({Loan.Status.ACTIVE, Loan.Status.PAID}),
    Loan.Status.PAID: frozenset(),
}


def add_months(date_value: date, months: int) -> date:
    """Suma meses a una fecha ajustando el día al último del mes destino.

    Args:
        date_value: fecha de partida.
        months: cantidad de meses a sumar.

    Returns:
        La fecha resultante.
    """
    month_index = date_value.month - 1 + months
    year = date_value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(date_value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def build_installment_schedule(
    principal: Decimal,
    annual_tna: Decimal,
    months: int,
    accepted_date: date,
) -> list[dict[str, Any]]:
    """Arma el cronograma de cuotas con amortización francesa.

    Todas las cuotas tienen el mismo importe; la **última** ajusta su parte de
    capital para que la suma de los capitales sea exactamente el principal, y
    su parte de interés absorbe el redondeo acumulado.

    Args:
        principal: capital del préstamo.
        annual_tna: tasa nominal anual en porcentaje.
        months: cantidad de cuotas.
        accepted_date: fecha de aceptación del préstamo.

    Returns:
        Lista con los datos de cada cuota.
    """
    installment = french_installment(principal=principal, annual_tna=annual_tna, months=months)
    monthly_rate = monthly_rate_from_annual_tna(annual_tna)
    remaining = principal
    principal_accumulated = Decimal('0.00')
    schedule = []
    for number in range(1, months + 1):
        if number == months:
            principal_part = round_two(principal - principal_accumulated)
            interest_part = round_two(installment - principal_part)
        else:
            interest_part = round_two(remaining * monthly_rate)
            principal_part = round_two(installment - interest_part)
        schedule.append(
            {
                'number': number,
                'due_date': add_months(accepted_date, number),
                'principal_amount': principal_part,
                'interest_amount': interest_part,
                'amount': round_two(principal_part + interest_part),
            }
        )
        principal_accumulated = round_two(principal_accumulated + principal_part)
        remaining = round_two(remaining - principal_part)
    return schedule


def accept_offer(
    borrower_user_id: uuid.UUID,
    offer_id: uuid.UUID,
    idempotency_key: str,
) -> Loan:
    """El prestatario acepta una oferta y recibe el préstamo.

    Todo el proceso es atómico: si el desembolso falla, la oferta vuelve a
    estar activa y no queda préstamo ni cuotas.

    Args:
        borrower_user_id: prestatario que acepta la oferta.
        offer_id: identificador de la oferta aceptada.
        idempotency_key: clave de idempotencia del prestatario.

    Returns:
        El Loan creado, o el original si la clave ya se usó.

    Raises:
        KYCNotCompleted: si el prestatario no tiene KYC aprobada.
        IdempotencyConflict: si la clave ya existe con otro payload.
        InsufficientFunds: si el prestamista no tiene saldo para desembolzar.
    """
    request_hash = ledger_services.build_request_hash({'offer_id': str(offer_id)})
    try:
        with transaction.atomic():
            existing = _resolve_idempotent(borrower_user_id, idempotency_key, request_hash)
            if existing is not None:
                return existing
            _require_kyc(borrower_user_id)
            offer = offers_services.accept_offer(
                offer_id=offer_id,
                borrower_user_id=borrower_user_id,
            )
            loan = Loan.objects.create(
                borrower_user_id=borrower_user_id,
                lender_user_id=offer.lender_user_id,
                offer_id=offer.id,
                principal=offer.amount,
                currency=offer.currency,
                interest_rate=offer.interest_rate,
                term_months=offer.term_months,
                status=Loan.Status.ACTIVE,
                accepted_at=timezone.now(),
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
            OfferTermsSnapshot.objects.create(
                loan=loan,
                accepted_at=loan.accepted_at,
                accepted_by_user_id=borrower_user_id,
                snapshot_data={
                    'offer_id': str(offer.id),
                    'lender_user_id': str(offer.lender_user_id),
                    'amount': str(offer.amount),
                    'currency': offer.currency,
                    'interest_rate': str(offer.interest_rate),
                    'term_months': offer.term_months,
                    'requirements': offer.requirements,
                },
                is_immutable=True,
            )
            _create_installments(loan)
            _disburse(loan)
            logger.info(
                'Préstamo aceptado: loan_id=%s offer_id=%s borrower_user_id=%s lender_user_id=%s',
                loan.id,
                offer.id,
                borrower_user_id,
                offer.lender_user_id,
            )
            return loan
    except IntegrityError:
        existing = _resolve_idempotent(borrower_user_id, idempotency_key, request_hash)
        if existing is None:
            raise
        return existing


def pay_installment(
    loan_id: uuid.UUID,
    number: int,
    borrower_user_id: uuid.UUID,
) -> Installment:
    """El prestatario paga una cuota del préstamo.

    Las cuotas se pagan **en orden** y por el importe completo. Al pagar la
    última, el préstamo pasa a `paid`.

    Args:
        loan_id: identificador del préstamo.
        number: número de cuota a pagar.
        borrower_user_id: prestatario que paga.

    Returns:
        La Installment pagada.

    Raises:
        LoanNotFound: si el préstamo no existe.
        NotTheBorrower: si quien paga no es el prestatario.
        InstallmentAlreadyPaid: si la cuota ya estaba pagada.
        InstallmentOutOfOrder: si la cuota anterior no está pagada.
        InsufficientFunds: si el prestatario no tiene saldo para pagar.
    """
    with transaction.atomic():
        loan = Loan.objects.select_for_update().filter(id=loan_id).first()
        if loan is None:
            raise LoanNotFound('El préstamo no existe.')
        if loan.borrower_user_id != borrower_user_id:
            raise NotTheBorrower('Solo el prestatario puede pagar las cuotas.')
        installment = (
            Installment.objects.select_for_update().filter(loan=loan, number=number).first()
        )
        if installment is None:
            raise LoanNotFound('La cuota no existe.')
        if installment.status == Installment.Status.PAID:
            raise InstallmentAlreadyPaid('La cuota ya está pagada.')
        previous = Installment.objects.filter(loan=loan, number=number - 1).first()
        if previous is not None and previous.status != Installment.Status.PAID:
            raise InstallmentOutOfOrder('Las cuotas se pagan en orden.')
        ledger_transaction = ledger_services.transfer_between_users(
            source_user_id=loan.borrower_user_id,
            destination_user_id=loan.lender_user_id,
            currency=loan.currency,
            amount=installment.amount,
            idempotency_key=f'loan-{loan.id}-installment-{number}',
            initiated_by_user_id=borrower_user_id,
            description=f'Pago de la cuota {number} del préstamo {loan.id}',
        )
        installment.status = Installment.Status.PAID
        installment.paid_at = timezone.now()
        installment.ledger_transaction_id = ledger_transaction.id
        installment.save(update_fields=['status', 'paid_at', 'ledger_transaction_id', 'updated_at'])
        _refresh_loan_status(loan)
        logger.info(
            'Cuota pagada: loan_id=%s number=%s borrower_user_id=%s',
            loan.id,
            number,
            borrower_user_id,
        )
        return installment


def change_loan_status(loan_id: uuid.UUID, new_status: str) -> Loan:
    """Cambia el estado del préstamo validando la transición.

    Args:
        loan_id: identificador del préstamo.
        new_status: estado destino.

    Returns:
        El Loan con el nuevo estado.

    Raises:
        LoanNotFound: si el préstamo no existe.
        InvalidLoanTransition: si la transición no es válida.
    """
    with transaction.atomic():
        loan = Loan.objects.select_for_update().filter(id=loan_id).first()
        if loan is None:
            raise LoanNotFound('El préstamo no existe.')
        _transition(loan, new_status)
        return loan


def mark_overdue(today: date) -> int:
    """Marca como vencidas las cuotas que ya pasaron su vencimiento.

    Las cuotas vencidas pasan a `overdue` y su préstamo a `defaulted`.

    Args:
        today: fecha de referencia.

    Returns:
        La cantidad de cuotas marcadas como vencidas.
    """
    pending = Installment.objects.filter(
        status=Installment.Status.PENDING,
        due_date__lt=today,
    ).select_related('loan')
    marked = 0
    for installment in pending:
        installment.status = Installment.Status.OVERDUE
        installment.save(update_fields=['status', 'updated_at'])
        _transition(installment.loan, Loan.Status.DEFAULTED)
        marked += 1
    if marked:
        logger.info('Cuotas vencidas marcadas: count=%s date=%s', marked, today)
    return marked


def _create_installments(loan: Loan) -> None:
    """Persiste el cronograma de cuotas del préstamo."""
    schedule = build_installment_schedule(
        principal=loan.principal,
        annual_tna=loan.interest_rate,
        months=loan.term_months,
        accepted_date=loan.accepted_at.date(),
    )
    for row in schedule:
        Installment.objects.create(loan=loan, **row)


def _disburse(loan: Loan) -> None:
    """Desembolsa el capital del préstamo del prestamista al prestatario."""
    ledger_transaction = ledger_services.transfer_between_users(
        source_user_id=loan.lender_user_id,
        destination_user_id=loan.borrower_user_id,
        currency=loan.currency,
        amount=loan.principal,
        idempotency_key=f'loan-{loan.id}-disbursement',
        initiated_by_user_id=loan.borrower_user_id,
        description=f'Desembolso del préstamo {loan.id}',
    )
    loan.ledger_transaction_id = ledger_transaction.id
    loan.save(update_fields=['ledger_transaction_id', 'updated_at'])


def _refresh_loan_status(loan: Loan) -> None:
    """Actualiza el estado del préstamo según sus cuotas."""
    statuses = [installment.status for installment in loan.installments.all()]
    if statuses and all(status == Installment.Status.PAID for status in statuses):
        _transition(loan, Loan.Status.PAID)
    elif any(status == Installment.Status.OVERDUE for status in statuses):
        _transition(loan, Loan.Status.DEFAULTED)
    else:
        _transition(loan, Loan.Status.ACTIVE)


def _transition(loan: Loan, new_status: str) -> None:
    """Cambia el estado del préstamo validando la transición.

    Raises:
        InvalidLoanTransition: si la transición no es válida.
    """
    if loan.status == new_status:
        return
    if new_status not in VALID_TRANSITIONS.get(loan.status, frozenset()):
        raise InvalidLoanTransition(
            f'No se puede pasar el préstamo de {loan.status} a {new_status}.'
        )
    loan.status = new_status
    loan.save(update_fields=['status', 'updated_at'])


def _resolve_idempotent(
    borrower_user_id: uuid.UUID,
    idempotency_key: str,
    request_hash: str,
) -> Loan | None:
    """Devuelve el préstamo original si la clave ya existe con el mismo payload.

    Raises:
        IdempotencyConflict: si la clave existe con un payload distinto.
    """
    existing = Loan.objects.filter(
        borrower_user_id=borrower_user_id,
        idempotency_key=idempotency_key,
    ).first()
    if existing is None:
        return None
    if existing.request_hash != request_hash:
        raise IdempotencyConflict('Ya existe un préstamo con esa clave de idempotencia.')
    return existing


def _require_kyc(borrower_user_id: uuid.UUID) -> None:
    """Exige KYC aprobada para tomar un préstamo (AGENTS §9.9).

    Raises:
        KYCNotCompleted: si el prestatario no tiene KYC aprobada.
    """
    if not is_kyc_approved(user_id=borrower_user_id):
        raise KYCNotCompleted('Necesitás completar la verificación KYC para tomar un préstamo.')
