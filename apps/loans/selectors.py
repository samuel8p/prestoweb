"""Selectores de lectura de la app loans (interfaz pública)."""

import uuid
from decimal import Decimal

from django.db.models import Q, QuerySet

from apps.loans.models import Installment, Loan


def get_loan_for_party(loan_id: uuid.UUID, user_id: uuid.UUID) -> Loan | None:
    """Devuelve el préstamo solo si el usuario es parte de él.

    Args:
        loan_id: identificador del préstamo.
        user_id: identificador del usuario.

    Returns:
        El Loan si el usuario es prestatario o prestamista, o None.
    """
    return Loan.objects.filter(
        Q(borrower_user_id=user_id) | Q(lender_user_id=user_id),
        id=loan_id,
    ).first()


def list_loans_for_user(user_id: uuid.UUID) -> QuerySet[Loan]:
    """Lista los préstamos en los que el usuario es parte.

    Args:
        user_id: identificador del usuario.

    Returns:
        QuerySet con los préstamos del usuario.
    """
    return (
        Loan.objects.filter(Q(borrower_user_id=user_id) | Q(lender_user_id=user_id))
        .prefetch_related('installments', 'terms_snapshot')
        .order_by('-accepted_at')
    )


def list_installments(loan_id: uuid.UUID) -> QuerySet[Installment]:
    """Lista las cuotas de un préstamo.

    Args:
        loan_id: identificador del préstamo.

    Returns:
        QuerySet con las cuotas ordenadas por número.
    """
    return Installment.objects.filter(loan_id=loan_id).order_by('number')


def list_loan_movement_breakdowns(transaction_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
    """Devuelve el desglose de los movimientos que pertenecen a un préstamo.

    El desglose tiene esta forma::

        {
            'kind': 'installment_payment' | 'loan_disbursement',
            'principal': Decimal,
            'interest': Decimal,
            'currency': str,
        }

    Solo devuelve primitivos: quien lo consume es otra app y no puede conocer
    los modelos de `loans`.

    Args:
        transaction_ids: identificadores de los movimientos del ledger.

    Returns:
        Dict con el desglose de cada movimiento que pertenece a un préstamo.
    """
    if not transaction_ids:
        return {}
    breakdowns: dict[uuid.UUID, dict] = {}
    installments = Installment.objects.filter(
        ledger_transaction_id__in=transaction_ids,
    ).select_related('loan')
    for installment in installments:
        breakdowns[installment.ledger_transaction_id] = {
            'kind': 'installment_payment',
            'principal': installment.principal_amount,
            'interest': installment.interest_amount,
            'currency': installment.loan.currency,
        }
    for loan in Loan.objects.filter(ledger_transaction_id__in=transaction_ids):
        breakdowns[loan.ledger_transaction_id] = {
            'kind': 'loan_disbursement',
            'principal': loan.principal,
            'interest': Decimal('0.00'),
            'currency': loan.currency,
        }
    return breakdowns


def get_loan_movement_breakdown(transaction_id: uuid.UUID) -> dict | None:
    """Devuelve el desglose de un movimiento de préstamo, o None si no lo es.

    Args:
        transaction_id: identificador del movimiento del ledger.

    Returns:
        El desglose del movimiento o None.
    """
    return list_loan_movement_breakdowns(transaction_ids=[transaction_id]).get(transaction_id)
