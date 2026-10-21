"""Selectores de lectura de la app matching (interfaz pública).

`matching` es **solo lectura**: no escribe estado y se apoya únicamente en
`offers.selectors` (nunca en `offers.models`), según AGENTS §Reglas de ofertas 5.
"""

import uuid
from decimal import Decimal
from typing import Any

from apps.core.money import french_installment, french_total_cost, french_total_interest
from apps.matching.exceptions import NotEnoughOffersToCompare, OfferNotFound
from apps.offers import selectors as offers_selectors

MIN_OFFERS_TO_COMPARE = 2


def search_offers(
    currency: str | None = None,
    amount: Decimal | None = None,
    max_rate: Decimal | None = None,
    term_months: int | None = None,
    ordering: str = 'rate',
) -> list[dict[str, Any]]:
    """Busca ofertas activas que coincidan con los filtros indicados.

    Args:
        currency: filtra por moneda.
        amount: monto **mínimo** que se necesita.
        max_rate: TNA anual máxima aceptada.
        term_months: plazo exacto en meses.
        ordering: criterio de orden (`rate`, `term` o `amount`).

    Returns:
        Lista de ofertas con sus datos serializables.
    """
    offers = offers_selectors.search_active_offers(
        currency=currency,
        amount=amount,
        max_rate=max_rate,
        term_months=term_months,
        ordering=ordering,
    )
    return [_offer_data(offer) for offer in offers]


def compare_offers(offer_ids: list[uuid.UUID]) -> list[dict[str, Any]]:
    """Compara dos o más ofertas activas.

    Para cada oferta devuelve la cuota mensual, el interés total y el costo
    total, calculados con las funciones de `core/money.py`.

    Args:
        offer_ids: identificadores de las ofertas a comparar.

    Returns:
        Lista con los datos de cada oferta y sus números.

    Raises:
        NotEnoughOffersToCompare: si se pasan menos de dos ofertas.
        OfferNotFound: si alguna oferta no existe o no está activa.
    """
    if len(offer_ids) < MIN_OFFERS_TO_COMPARE:
        raise NotEnoughOffersToCompare('Hacen falta al menos dos ofertas para comparar.')
    compared = []
    for offer_id in offer_ids:
        offer = offers_selectors.get_active_offer(offer_id=offer_id)
        if offer is None:
            raise OfferNotFound('La oferta no existe o no está activa.')
        data = _offer_data(offer)
        data['installment'] = french_installment(
            principal=data['amount'],
            annual_tna=data['interest_rate'],
            months=data['term_months'],
        )
        data['total_interest'] = french_total_interest(
            principal=data['amount'],
            annual_tna=data['interest_rate'],
            months=data['term_months'],
        )
        data['total_cost'] = french_total_cost(
            principal=data['amount'],
            annual_tna=data['interest_rate'],
            months=data['term_months'],
        )
        compared.append(data)
    return compared


def _offer_data(offer) -> dict[str, Any]:
    """Arma los datos serializables de una oferta."""
    return {
        'id': offer.id,
        'lender_user_id': offer.lender_user_id,
        'amount': offer.amount,
        'currency': offer.currency,
        'interest_rate': offer.interest_rate,
        'term_months': offer.term_months,
        'requirements': offer.requirements,
    }
