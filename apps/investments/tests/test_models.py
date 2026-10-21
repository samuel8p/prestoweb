"""Tests de los modelos de investments."""

import uuid
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.investments.tests.factories import InvestmentProductFactory, PositionFactory

pytestmark = pytest.mark.django_db


def test_product_defaults_to_active_fixed_term():
    """Un producto nuevo nace activo y de plazo fijo."""
    from apps.investments.models import InvestmentProduct

    product = InvestmentProductFactory()

    assert product.status == InvestmentProduct.Status.ACTIVE
    assert product.type == InvestmentProduct.Type.FIXED_TERM
    assert product.term_days == 30


def test_product_term_days_must_be_positive():
    """El plazo del producto debe ser mayor que cero."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            InvestmentProductFactory(term_days=0)


def test_product_annual_rate_must_be_positive():
    """La tasa del producto debe ser mayor que cero."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            InvestmentProductFactory(annual_rate_tna=Decimal('0.00'))


def test_product_min_amount_must_be_positive():
    """El monto mínimo del producto debe ser mayor que cero."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            InvestmentProductFactory(min_amount=Decimal('0.00'))


def test_position_defaults_to_active():
    """Una posición nueva nace activa."""
    from apps.investments.models import Position

    position = PositionFactory()

    assert position.status == Position.Status.ACTIVE
    assert position.amount == Decimal('5000.00')


def test_position_amount_must_be_positive():
    """El monto de la posición debe ser mayor que cero."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PositionFactory(amount=Decimal('0.00'))


def test_position_interest_must_be_non_negative():
    """El interés de la posición no puede ser negativo."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PositionFactory(interest_amount=Decimal('-1.00'))


def test_position_idempotency_key_is_unique_per_user():
    """La clave de idempotencia es única por usuario."""
    user_id = uuid.uuid4()
    PositionFactory(user_id=user_id, idempotency_key='k1')

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PositionFactory(user_id=user_id, idempotency_key='k1')


def test_position_idempotency_key_can_repeat_for_another_user():
    """Dos usuarios distintos pueden usar la misma clave."""
    PositionFactory(user_id=uuid.uuid4(), idempotency_key='k1')
    PositionFactory(user_id=uuid.uuid4(), idempotency_key='k1')

    from apps.investments.models import Position

    assert Position.objects.filter(idempotency_key='k1').count() == 2


def test_position_product_cannot_be_deleted():
    """Un producto con posiciones no se puede borrar."""
    from apps.investments.models import InvestmentProduct

    product = InvestmentProductFactory()
    PositionFactory(product=product)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            product.delete()
