"""Modelos del libro mayor de doble entrada."""

import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class Account(BaseModel):
    """Cuenta de un usuario o cuenta de contrapartida del sistema.

    El saldo vive desnormalizado en ``balance`` y solo se modifica desde
    ``services.py`` bajo ``select_for_update()``.
    """

    class Kind(models.TextChoices):
        USER_WALLET = 'user_wallet', 'Billetera de usuario'
        CUSTODY = 'custody', 'Custodia'
        SYSTEM = 'system', 'Sistema'

    class Currency(models.TextChoices):
        ARS = 'ARS', 'Peso argentino'
        USD = 'USD', 'Dólar'

    user_id = models.UUIDField(null=True, blank=True)
    currency = models.CharField(max_length=3, choices=Currency.choices)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'currency'],
                condition=models.Q(kind='user_wallet'),
                name='ledger_account_one_user_wallet_per_currency',
            ),
            models.UniqueConstraint(
                fields=['kind', 'currency'],
                condition=models.Q(kind__in=['custody', 'system']),
                name='ledger_account_one_counterpart_per_kind_currency',
            ),
            models.CheckConstraint(
                condition=models.Q(kind='user_wallet', user_id__isnull=False)
                | models.Q(kind__in=['custody', 'system'], user_id__isnull=True),
                name='ledger_account_user_presence_matches_kind',
            ),
            models.CheckConstraint(
                condition=~models.Q(kind='user_wallet') | models.Q(balance__gte=0),
                name='ledger_account_user_wallet_balance_non_negative',
            ),
        ]

    def __str__(self):
        return f'Account<{self.kind}:{self.currency}:{self.balance}>'


class LedgerTransaction(BaseModel):
    """Movimiento de dinero: agrupa los asientos de una operación."""

    class Type(models.TextChoices):
        DEPOSIT = 'deposit', 'Depósito'
        WITHDRAWAL = 'withdrawal', 'Retiro'
        TRANSFER = 'transfer', 'Transferencia'
        INTEREST = 'interest', 'Interés'
        FEE = 'fee', 'Comisión'
        REVERSAL = 'reversal', 'Reverso'

    type = models.CharField(max_length=16, choices=Type.choices)
    idempotency_key = models.CharField(max_length=100)
    request_hash = models.CharField(max_length=64)
    created_by_user_id = models.UUIDField()
    destination_account_id = models.UUIDField(null=True, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    description = models.CharField(max_length=255, blank=True)
    reverses = models.OneToOneField(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reversal',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['created_by_user_id', 'idempotency_key'],
                name='ledger_transaction_idempotency_per_user',
            ),
        ]

    def __str__(self):
        return f'LedgerTransaction<{self.type}:{self.idempotency_key}>'


class LedgerEntry(BaseModel):
    """Asiento de un movimiento: un débito o un crédito sobre una cuenta."""

    class Direction(models.TextChoices):
        DEBIT = 'debit', 'Débito'
        CREDIT = 'credit', 'Crédito'

    ledger_transaction = models.ForeignKey(
        LedgerTransaction,
        on_delete=models.PROTECT,
        related_name='entries',
    )
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='entries')
    direction = models.CharField(max_length=6, choices=Direction.choices)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Account.Currency.choices)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='ledger_entry_amount_positive',
            ),
        ]

    def __str__(self):
        return f'LedgerEntry<{self.direction}:{self.amount}>'
