"""Selectores de lectura de la app investments (interfaz pública)."""

import uuid

from django.db.models import QuerySet

from apps.investments.models import InvestmentProduct, Position


def list_active_products() -> QuerySet[InvestmentProduct]:
    """Lista los productos de inversión activos.

    Returns:
        QuerySet con los productos activos.
    """
    return InvestmentProduct.objects.filter(
        status=InvestmentProduct.Status.ACTIVE,
    ).order_by('annual_rate_tna', 'term_days')


def list_positions_for_user(user_id: uuid.UUID) -> QuerySet[Position]:
    """Lista las posiciones de inversión del usuario.

    Args:
        user_id: identificador del usuario.

    Returns:
        QuerySet con las posiciones del usuario.
    """
    return Position.objects.filter(user_id=user_id).select_related('product').order_by('-opened_at')


def get_position_for_user(
    position_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Position | None:
    """Devuelve la posición del usuario, o None si no existe o es de otro.

    Args:
        position_id: identificador de la posición.
        user_id: identificador del usuario.

    Returns:
        La Position del usuario o None.
    """
    return (
        Position.objects.filter(id=position_id, user_id=user_id).select_related('product').first()
    )
