"""Modelos de ofertas de préstamo."""

import uuid

from django.db import models

from apps.core.models import BaseModel


class Offer(BaseModel):
    """Oferta de préstamo publicada por un prestamista.

    Publicar una oferta **no reserva fondos**: la reserva ocurre recién
    cuando el préstamo se acepta (Fase 3, `loans`).
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Activa'
        EXPIRED = 'expired', 'Expirada'
        ACCEPTED = 'accepted', 'Aceptada'

    class Currency(models.TextChoices):
        ARS = 'ARS', 'Peso argentino'
        USD = 'USD', 'Dólar'

    lender_user_id = models.UUIDField()
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices)
    interest_rate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text='TNA anual en porcentaje (ej. 24.00 = 24% TNA).',
    )
    term_months = models.PositiveIntegerField()
    requirements = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='offers_offer_amount_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(interest_rate__gt=0),
                name='offers_offer_interest_rate_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(term_months__gt=0),
                name='offers_offer_term_months_positive',
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'Offer<{self.id}:{self.amount}:{self.currency}>'
