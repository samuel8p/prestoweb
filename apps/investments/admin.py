"""Administración de Django para la app investments.

Los productos de inversión se dan de alta únicamente desde acá, que solo es
accesible para usuarios staff.
"""

from django.contrib import admin

from apps.investments.models import InvestmentProduct, Position


@admin.register(InvestmentProduct)
class InvestmentProductAdmin(admin.ModelAdmin):
    """Alta y edición de productos de inversión a plazo fijo."""

    list_display = [
        'id',
        'type',
        'currency',
        'term_days',
        'annual_rate_tna',
        'min_amount',
        'status',
    ]
    list_filter = ['type', 'status', 'currency']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    """Consulta de las posiciones de inversión abiertas."""

    list_display = ['id', 'user_id', 'product', 'amount', 'status', 'opened_at', 'maturity_date']
    list_filter = ['status', 'product']
    readonly_fields = [
        'id',
        'user_id',
        'product',
        'amount',
        'status',
        'opened_at',
        'maturity_date',
        'interest_amount',
        'idempotency_key',
        'request_hash',
        'created_at',
        'updated_at',
    ]

    def has_add_permission(self, request):
        """Las posiciones se crean únicamente desde los servicios de investments."""
        return False

    def has_change_permission(self, request, obj=None):
        """Las posiciones no se editan a mano."""
        return False
