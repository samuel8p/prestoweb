"""Modelos de préstamos."""

import uuid

from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class Loan(BaseModel):
    """Préstamo aceptado a partir de una oferta publicada.

    El préstamo nace `active`: el estado `pending` no se usa.
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Activo'
        PAID = 'paid', 'Pagado'
        DEFAULTED = 'defaulted', 'En mora'

    class Currency(models.TextChoices):
        ARS = 'ARS', 'Peso argentino'
        USD = 'USD', 'Dólar'

    borrower_user_id = models.UUIDField()
    lender_user_id = models.UUIDField()
    offer_id = models.UUIDField()
    principal = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices)
    interest_rate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text='TNA anual en porcentaje (ej. 24.00 = 24% TNA).',
    )
    term_months = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    accepted_at = models.DateTimeField(default=timezone.now)
    idempotency_key = models.CharField(max_length=100)
    request_hash = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['borrower_user_id', 'idempotency_key'],
                name='loans_loan_idempotency_per_borrower',
            ),
            models.CheckConstraint(
                condition=models.Q(principal__gt=0),
                name='loans_loan_principal_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(term_months__gt=0),
                name='loans_loan_term_months_positive',
            ),
        ]
        ordering = ['-accepted_at']

    def __str__(self):
        return f'Loan<{self.id}:{self.principal}:{self.status}>'


class OfferTermsSnapshot(BaseModel):
    """Snapshot inmutable de los términos de la oferta aceptada."""

    loan = models.OneToOneField(Loan, on_delete=models.PROTECT, related_name='terms_snapshot')
    accepted_at = models.DateTimeField(default=timezone.now)
    accepted_by_user_id = models.UUIDField()
    snapshot_data = models.JSONField()
    is_immutable = models.BooleanField(default=True)

    def __str__(self):
        return f'OfferTermsSnapshot<{self.loan_id}>'


class Installment(BaseModel):
    """Cuota de un préstamo, con su parte de capital y su parte de interés."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        PAID = 'paid', 'Pagada'
        OVERDUE = 'overdue', 'Vencida'

    loan = models.ForeignKey(Loan, on_delete=models.PROTECT, related_name='installments')
    number = models.PositiveIntegerField()
    due_date = models.DateField()
    principal_amount = models.DecimalField(max_digits=18, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=18, decimal_places=2)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['loan', 'number'],
                name='loans_installment_unique_number_per_loan',
            ),
            models.CheckConstraint(
                condition=models.Q(principal_amount__gt=0),
                name='loans_installment_principal_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(interest_amount__gte=0),
                name='loans_installment_interest_non_negative',
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='loans_installment_amount_positive',
            ),
        ]
        ordering = ['loan_id', 'number']

    def __str__(self):
        return f'Installment<{self.loan_id}:{self.number}:{self.amount}>'
