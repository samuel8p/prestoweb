"""Servicios de escritura de la app investments (interfaz pública)."""

import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.exceptions import KYCNotCompleted
from apps.core.money import simple_interest
from apps.identity.selectors import is_kyc_approved
from apps.investments.exceptions import (
    InsufficientInvestmentAmount,
    ProductNotActive,
    ProductNotFound,
)
from apps.investments.models import Position
from apps.ledger import services as ledger_services
from apps.ledger.exceptions import CurrencyMismatch, IdempotencyConflict

logger = logging.getLogger(__name__)


def add_days(date_value: date, days: int) -> date:
    """Suma días corridos a una fecha.

    Args:
        date_value: fecha de partida.
        days: cantidad de días a sumar.

    Returns:
        La fecha resultante.
    """
    return date_value + timedelta(days=days)


def open_position(
    user_id: uuid.UUID,
    product_id: uuid.UUID,
    amount: Decimal,
    idempotency_key: str,
    currency: str | None = None,
) -> Position:
    """Abre una posición de inversión a plazo fijo.

    Todo el proceso es atómico: si el movimiento de fondos falla, no queda
    posición ni saldo movido.

    Args:
        user_id: usuario que invierte.
        product_id: producto de inversión elegido.
        amount: monto a invertir, mayor o igual al mínimo del producto.
        idempotency_key: clave de idempotencia del usuario.
        currency: moneda esperada; si se informa, debe coincidir con la del
            producto.

    Returns:
        La Position creada, o la original si la clave ya se usó.

    Raises:
        KYCNotCompleted: si el usuario no tiene KYC aprobada.
        ProductNotFound: si el producto no existe.
        ProductNotActive: si el producto no admite nuevas inversiones.
        InsufficientInvestmentAmount: si el monto es menor al mínimo.
        CurrencyMismatch: si la moneda no coincide con la del producto.
        IdempotencyConflict: si la clave ya existe con otro payload.
    """
    request_hash = ledger_services.build_request_hash(
        {
            'product_id': str(product_id),
            'amount': str(amount),
            'currency': currency or '',
        }
    )
    try:
        with transaction.atomic():
            existing = _resolve_idempotent(user_id, idempotency_key, request_hash)
            if existing is not None:
                return existing
            _require_kyc(user_id)
            product = _get_active_product(product_id)
            if currency is not None and currency != product.currency:
                raise CurrencyMismatch('La moneda debe coincidir con la del producto.')
            if amount < product.min_amount:
                raise InsufficientInvestmentAmount('El monto es menor al mínimo del producto.')
            interest = simple_interest(
                amount=amount,
                annual_tna=product.annual_rate_tna,
                days=product.term_days,
            )
            opened_at = timezone.now()
            position = Position.objects.create(
                user_id=user_id,
                product=product,
                amount=amount,
                status=Position.Status.ACTIVE,
                opened_at=opened_at,
                maturity_date=add_days(opened_at.date(), product.term_days),
                interest_amount=interest,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
            ledger_services.transfer_to_counterpart(
                user_id=user_id,
                counterparty_kind=ledger_services.SYSTEM_COUNTERPART,
                currency=product.currency,
                amount=amount,
                idempotency_key=f'investment-{position.id}-opening',
                initiated_by_user_id=user_id,
                description=f'Apertura de la inversión {position.id}',
            )
            logger.info(
                'Posición de inversión abierta: position_id=%s user_id=%s amount=%s',
                position.id,
                user_id,
                amount,
            )
            return position
    except IntegrityError:
        existing = _resolve_idempotent(user_id, idempotency_key, request_hash)
        if existing is None:
            raise
        return existing


def settle_matured_positions(today: date) -> int:
    """Liquida las posiciones vencidas, pagando capital e interés.

    La liquidación ocurre **una sola vez por posición**: si la posición ya
    está `matured` se omite, y los movimientos del ledger son idempotentes.

    Args:
        today: fecha de referencia.

    Returns:
        La cantidad de posiciones liquidadas.
    """
    pending = Position.objects.filter(
        status=Position.Status.ACTIVE,
        maturity_date__lte=today,
    ).order_by('maturity_date')
    settled = 0
    for position in pending:
        if _settle_position(position):
            settled += 1
    if settled:
        logger.info('Posiciones liquidadas: count=%s date=%s', settled, today)
    return settled


def _settle_position(position: Position) -> bool:
    """Liquida una posición: devuelve True si efectivamente se liquidó."""
    with transaction.atomic():
        locked = Position.objects.select_for_update().filter(pk=position.pk).first()
        if locked is None or locked.status != Position.Status.ACTIVE:
            return False
        currency = locked.product.currency
        ledger_services.transfer_from_counterpart(
            user_id=locked.user_id,
            counterparty_kind=ledger_services.SYSTEM_COUNTERPART,
            currency=currency,
            amount=locked.amount,
            idempotency_key=f'investment-{locked.id}-capital',
            initiated_by_user_id=locked.user_id,
            description=f'Reembolso del capital de la inversión {locked.id}',
        )
        if locked.interest_amount > 0:
            ledger_services.transfer_from_counterpart(
                user_id=locked.user_id,
                counterparty_kind=ledger_services.SYSTEM_COUNTERPART,
                currency=currency,
                amount=locked.interest_amount,
                idempotency_key=f'investment-{locked.id}-interest',
                initiated_by_user_id=locked.user_id,
                movement_type=ledger_services.INTEREST_MOVEMENT_TYPE,
                description=f'Interés de la inversión {locked.id}',
            )
        locked.status = Position.Status.MATURED
        locked.save(update_fields=['status', 'updated_at'])
    return True


def _get_active_product(product_id: uuid.UUID):
    """Devuelve el producto activo indicado.

    Raises:
        ProductNotFound: si el producto no existe.
        ProductNotActive: si el producto no admite nuevas inversiones.
    """
    product = _get_product(product_id)
    if product.status != product.Status.ACTIVE:
        raise ProductNotActive('El producto no admite nuevas inversiones.')
    return product


def _get_product(product_id: uuid.UUID):
    """Devuelve el producto indicado o falla.

    Raises:
        ProductNotFound: si el producto no existe.
    """
    from apps.investments.models import InvestmentProduct

    product = InvestmentProduct.objects.filter(id=product_id).first()
    if product is None:
        raise ProductNotFound('El producto de inversión no existe.')
    return product


def _resolve_idempotent(
    user_id: uuid.UUID,
    idempotency_key: str,
    request_hash: str,
) -> Position | None:
    """Devuelve la posición original si la clave ya existe con el mismo payload.

    Raises:
        IdempotencyConflict: si la clave existe con un payload distinto.
    """
    existing = Position.objects.filter(
        user_id=user_id,
        idempotency_key=idempotency_key,
    ).first()
    if existing is None:
        return None
    if existing.request_hash != request_hash:
        raise IdempotencyConflict('Ya existe una inversión con esa clave de idempotencia.')
    return existing


def _require_kyc(user_id: uuid.UUID) -> None:
    """Exige KYC aprobada para invertir (AGENTS §9.9).

    Raises:
        KYCNotCompleted: si el usuario no tiene KYC aprobada.
    """
    if not is_kyc_approved(user_id=user_id):
        raise KYCNotCompleted('Necesitás completar la verificación KYC para invertir.')
