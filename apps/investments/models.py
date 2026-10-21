"""Modelos de inversión a plazo fijo."""

import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class InvestmentProduct(BaseModel):
    """Producto de inversión a plazo fijo.

    Los productos se dan de alta únicamente desde el admin de Django
    (solo staff); la API solo los lista.
    """

    class Type(models.TextChoices):
        FIXED_TERM = 'fixed_term', 'Plazo fijo'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Activo'
        MATURED = 'matured', 'Vencido'
        CANCELLED = 'cancelled', 'Cancelado'

    class Currency(models.TextChoices):
        ARS = 'ARS', 'Peso argentino'
        USD = 'USD', 'Dólar'

    type = models.CharField(max_length=16, choices=Type.choices, default=Type.FIXED_TERM)
    currency = models.CharField(max_length=3, choices=Currency.choices)
    term_days = models.PositiveIntegerField()
    annual_rate_tna = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text='TNA anual en porcentaje (ej. 12.00 = 12% TNA).',
    )
    min_amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(term_days__gt=0),
                name='investments_product_term_days_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(annual_rate_tna__gt=0),
                name='investments_product_annual_rate_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(min_amount__gt=0),
                name='investments_product_min_amount_positive',
            ),
        ]
        ordering = ['annual_rate_tna', 'term_days']

    def __str__(self):
        return f'InvestmentProduct<{self.id}:{self.currency}:{self.term_days}d>'


class Position(BaseModel):
    """Posición de inversión abierta por un usuario."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Activa'
        MATURED = 'matured', 'Vencida'

    user_id = models.UUIDField()
    product = models.ForeignKey(
        InvestmentProduct,
        on_delete=models.PROTECT,
        related_name='positions',
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    opened_at = models.DateTimeField(default=timezone.now)
    maturity_date = models.DateField()
    interest_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    idempotency_key = models.CharField(max_length=100)
    request_hash = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'idempotency_key'],
                name='investments_position_idempotency_per_user',
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='investments_position_amount_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(interest_amount__gte=0),
                name='investments_position_interest_non_negative',
            ),
        ]
        ordering = ['-opened_at']

    def __str__(self):
        return f'Position<{self.id}:{self.amount}:{self.status}>'
