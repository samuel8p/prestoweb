"""Selectores de lectura de la app loans (interfaz pública)."""

import uuid

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
