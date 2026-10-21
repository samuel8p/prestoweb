"""Selectores de lectura de la app offers (interfaz pública)."""

import uuid
from decimal import Decimal

from django.db.models import QuerySet

from apps.offers.models import Offer

ORDERINGS = {
    'rate': ('interest_rate', 'term_months', 'amount'),
    'term': ('term_months', 'interest_rate', 'amount'),
    'amount': ('amount', 'interest_rate', 'term_months'),
}


def get_offer(offer_id: uuid.UUID, lender_user_id: uuid.UUID) -> Offer | None:
    """Devuelve la oferta del prestamista, o None si no existe o es de otro.

    Args:
        offer_id: identificador de la oferta.
        lender_user_id: identificador del prestamista.

    Returns:
        La Offer del prestamista o None.
    """
    return Offer.objects.filter(id=offer_id, lender_user_id=lender_user_id).first()


def list_offers_for_lender(lender_user_id: uuid.UUID) -> QuerySet[Offer]:
    """Lista las ofertas publicadas por el prestamista.

    Args:
        lender_user_id: identificador del prestamista.

    Returns:
        QuerySet con las ofertas del prestamista.
    """
    return Offer.objects.filter(lender_user_id=lender_user_id).order_by('-created_at')


def get_active_offer(offer_id: uuid.UUID) -> Offer | None:
    """Devuelve la oferta solo si está activa.

    Args:
        offer_id: identificador de la oferta.

    Returns:
        La Offer activa o None.
    """
    return Offer.objects.filter(id=offer_id, status=Offer.Status.ACTIVE).first()


def search_active_offers(
    currency: str | None = None,
    amount: Decimal | None = None,
    max_rate: Decimal | None = None,
    term_months: int | None = None,
    ordering: str = 'rate',
) -> QuerySet[Offer]:
    """Busca ofertas activas aplicando los filtros indicados.

    Args:
        currency: filtra por moneda.
        amount: monto **mínimo** que se necesita: ofertas con importe igual o mayor.
        max_rate: TNA anual máxima aceptada.
        term_months: plazo exacto en meses.
        ordering: criterio de orden (`rate`, `term` o `amount`).

    Returns:
        QuerySet con las ofertas activas que cumplen los filtros.
    """
    queryset = Offer.objects.filter(status=Offer.Status.ACTIVE)
    if currency:
        queryset = queryset.filter(currency=currency)
    if amount is not None:
        queryset = queryset.filter(amount__gte=amount)
    if max_rate is not None:
        queryset = queryset.filter(interest_rate__lte=max_rate)
    if term_months is not None:
        queryset = queryset.filter(term_months=term_months)
    return queryset.order_by(*ORDERINGS.get(ordering, ORDERINGS['rate']))
