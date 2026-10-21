"""Servicios de escritura de la app offers (interfaz pública)."""

import logging
import uuid
from decimal import Decimal

from django.db import transaction

from apps.core.exceptions import InvalidAmount, KYCNotCompleted
from apps.identity.selectors import is_kyc_approved
from apps.offers import selectors as offers_selectors
from apps.offers.exceptions import (
    CannotAcceptOwnOffer,
    OfferNotAcceptable,
    OfferNotEditable,
    OfferNotFound,
)
from apps.offers.models import Offer

logger = logging.getLogger(__name__)

EDITABLE_FIELDS = ('amount', 'currency', 'interest_rate', 'term_months', 'requirements')


def create_offer(
    lender_user_id: uuid.UUID,
    amount: Decimal,
    currency: str,
    interest_rate: Decimal,
    term_months: int,
    requirements: str = '',
) -> Offer:
    """Publica una oferta de préstamo.

    Publicar **no reserva fondos**: solo deja registrada la oferta.

    Args:
        lender_user_id: prestamista que publica la oferta.
        amount: monto a prestar, mayor que cero.
        currency: código ISO de la moneda.
        interest_rate: TNA anual en porcentaje.
        term_months: plazo en meses.
        requirements: requisitos en texto libre.

    Returns:
        La Offer creada, en estado active.

    Raises:
        KYCNotCompleted: si el prestamista no tiene KYC aprobada.
        InvalidAmount: si el monto, la tasa o el plazo no son válidos.
    """
    _require_kyc(lender_user_id)
    _assert_valid_offer(amount=amount, interest_rate=interest_rate, term_months=term_months)
    offer = Offer.objects.create(
        lender_user_id=lender_user_id,
        amount=amount,
        currency=currency,
        interest_rate=interest_rate,
        term_months=term_months,
        requirements=requirements,
        status=Offer.Status.ACTIVE,
    )
    logger.info(
        'Oferta publicada: offer_id=%s lender_user_id=%s amount=%s currency=%s',
        offer.id,
        lender_user_id,
        amount,
        currency,
    )
    return offer


def update_offer(
    offer_id: uuid.UUID,
    lender_user_id: uuid.UUID,
    amount: Decimal | None = None,
    currency: str | None = None,
    interest_rate: Decimal | None = None,
    term_months: int | None = None,
    requirements: str | None = None,
) -> Offer:
    """Actualiza los datos de una oferta activa del prestamista.

    Args:
        offer_id: identificador de la oferta.
        lender_user_id: prestamista dueño de la oferta.
        amount: nuevo monto, si cambia.
        currency: nueva moneda, si cambia.
        interest_rate: nueva TNA anual, si cambia.
        term_months: nuevo plazo, si cambia.
        requirements: nuevos requisitos, si cambian.

    Returns:
        La Offer actualizada.

    Raises:
        OfferNotFound: si la oferta no existe o es de otro prestamista.
        OfferNotEditable: si la oferta ya no está activa.
        KYCNotCompleted: si el prestamista no tiene KYC aprobada.
        InvalidAmount: si los valores nuevos no son válidos.
    """
    with transaction.atomic():
        offer = _get_own_offer_locked(offer_id=offer_id, lender_user_id=lender_user_id)
        if offer.status != Offer.Status.ACTIVE:
            raise OfferNotEditable('Solo se pueden modificar ofertas activas.')
        _require_kyc(lender_user_id)
        changes = {
            'amount': amount,
            'currency': currency,
            'interest_rate': interest_rate,
            'term_months': term_months,
            'requirements': requirements,
        }
        changes = {field: value for field, value in changes.items() if value is not None}
        _assert_valid_offer(
            amount=changes.get('amount', offer.amount),
            interest_rate=changes.get('interest_rate', offer.interest_rate),
            term_months=changes.get('term_months', offer.term_months),
        )
        for field, value in changes.items():
            setattr(offer, field, value)
        offer.save(update_fields=[*EDITABLE_FIELDS, 'updated_at'])
    return offer


def expire_offer(offer_id: uuid.UUID, lender_user_id: uuid.UUID) -> Offer:
    """Expira una oferta activa del prestamista.

    Args:
        offer_id: identificador de la oferta.
        lender_user_id: prestamista dueño de la oferta.

    Returns:
        La Offer expirada.

    Raises:
        OfferNotFound: si la oferta no existe o es de otro prestamista.
        OfferNotEditable: si la oferta ya no está activa.
    """
    with transaction.atomic():
        offer = _get_own_offer_locked(offer_id=offer_id, lender_user_id=lender_user_id)
        if offer.status != Offer.Status.ACTIVE:
            raise OfferNotEditable('Solo se pueden expirar ofertas activas.')
        offer.status = Offer.Status.EXPIRED
        offer.save(update_fields=['status', 'updated_at'])
    logger.info('Oferta expirada: offer_id=%s lender_user_id=%s', offer.id, lender_user_id)
    return offer


def accept_offer(offer_id: uuid.UUID, borrower_user_id: uuid.UUID) -> Offer:
    """Marca la oferta como aceptada por el prestatario.

    La oferta se bloquea (`select_for_update`) para que dos prestatarios no
    puedan aceptarla a la vez.

    Args:
        offer_id: identificador de la oferta.
        borrower_user_id: prestatario que la acepta.

    Returns:
        La Offer aceptada.

    Raises:
        OfferNotFound: si la oferta no existe.
        OfferNotAcceptable: si la oferta no está activa.
        CannotAcceptOwnOffer: si el prestatario es el prestamista.
    """
    with transaction.atomic():
        offer = offers_selectors.get_offer_locked(offer_id=offer_id)
        if offer is None:
            raise OfferNotFound('La oferta no existe.')
        if offer.status != Offer.Status.ACTIVE:
            raise OfferNotAcceptable('La oferta no está activa.')
        if offer.lender_user_id == borrower_user_id:
            raise CannotAcceptOwnOffer('No podés aceptar tu propia oferta.')
        offer.status = Offer.Status.ACCEPTED
        offer.save(update_fields=['status', 'updated_at'])
    logger.info(
        'Oferta aceptada: offer_id=%s lender_user_id=%s borrower_user_id=%s',
        offer.id,
        offer.lender_user_id,
        borrower_user_id,
    )
    return offer


def _get_own_offer_locked(offer_id: uuid.UUID, lender_user_id: uuid.UUID) -> Offer:
    """Devuelve la oferta del prestamista bloqueada, o falla.

    El bloqueo (`select_for_update`) serializa las escrituras sobre la misma
    oferta: sin él, dos actualizaciones simultáneas parten de la misma versión
    vieja y la última en guardar pisa a la otra.

    Raises:
        OfferNotFound: si la oferta no existe o es de otro prestamista.
    """
    offer = offers_selectors.get_own_offer_locked(
        offer_id=offer_id,
        lender_user_id=lender_user_id,
    )
    if offer is None:
        raise OfferNotFound('La oferta no existe.')
    return offer


def _assert_valid_offer(
    amount: Decimal,
    interest_rate: Decimal,
    term_months: int,
) -> None:
    """Verifica que los datos de la oferta sean válidos.

    Raises:
        InvalidAmount: si el monto, la tasa o el plazo no son válidos.
    """
    if amount <= 0:
        raise InvalidAmount('El monto de la oferta debe ser mayor que cero.')
    if interest_rate <= 0:
        raise InvalidAmount('La tasa de la oferta debe ser mayor que cero.')
    if term_months <= 0:
        raise InvalidAmount('El plazo de la oferta debe ser mayor que cero.')


def _require_kyc(lender_user_id: uuid.UUID) -> None:
    """Exige KYC aprobada para publicar ofertas (AGENTS §Reglas de ofertas 4).

    Raises:
        KYCNotCompleted: si el prestamista no tiene KYC aprobada.
    """
    if not is_kyc_approved(user_id=lender_user_id):
        raise KYCNotCompleted('Necesitás completar la verificación KYC para publicar ofertas.')
