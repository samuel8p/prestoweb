"""Administración de Django para la app ledger."""

from django.contrib import admin

from apps.ledger.exceptions import LedgerError
from apps.ledger.models import Account, LedgerEntry, LedgerTransaction
from apps.ledger.services import reverse_transaction


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    """Listado de cuentas del libro mayor."""

    list_display = ['id', 'kind', 'currency', 'user_id', 'balance']
    list_filter = ['kind', 'currency']
    search_fields = ['user_id']
    readonly_fields = ['id', 'balance', 'created_at', 'updated_at']


@admin.register(LedgerTransaction)
class LedgerTransactionAdmin(admin.ModelAdmin):
    """Gestión de los movimientos del libro mayor.

    Los movimientos son inmutables: la única operación disponible es el
    reverso, que crea una transacción compensatoria.
    """

    list_display = ['id', 'type', 'idempotency_key', 'created_by_user_id', 'occurred_at']
    list_filter = ['type', 'occurred_at']
    search_fields = ['idempotency_key', 'created_by_user_id']
    readonly_fields = [
        'id',
        'type',
        'idempotency_key',
        'request_hash',
        'created_by_user_id',
        'destination_account_id',
        'occurred_at',
        'description',
        'reverses',
    ]
    actions = ['reverse_transactions']

    @admin.action(description='Reversar los movimientos seleccionados')
    def reverse_transactions(self, request, queryset):
        """Revierte los movimientos seleccionados que todavía no fueron reversados."""
        reversed_count = 0
        for ledger_transaction in queryset:
            try:
                reverse_transaction(
                    transaction_id=ledger_transaction.id,
                    staff_user_id=request.user.id,
                )
            except LedgerError:
                continue
            reversed_count += 1
        self.message_user(request, f'{reversed_count} movimiento(s) reversado(s).')


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    """Listado de asientos del libro mayor (solo lectura)."""

    list_display = ['id', 'ledger_transaction', 'account', 'direction', 'amount', 'currency']
    list_filter = ['direction', 'currency']
    readonly_fields = ['id', 'ledger_transaction', 'account', 'direction', 'amount', 'currency']

    def has_add_permission(self, request):
        """Los asientos se crean únicamente desde los servicios del ledger."""
        return False

    def has_change_permission(self, request, obj=None):
        """Los asientos son inmutables."""
        return False
