"""Administración de Django para la app budgets.

Las categorías y los presupuestos los crea el usuario desde la API: el admin
solo permite consultarlos.
"""

from django.contrib import admin

from apps.budgets.models import Budget, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Consulta de las categorías de gasto."""

    list_display = ['id', 'user_id', 'name', 'created_at']
    search_fields = ['name', 'user_id']
    readonly_fields = ['id', 'user_id', 'name', 'created_at', 'updated_at']

    def has_add_permission(self, request):
        """Las categorías se crean únicamente desde los servicios de budgets."""
        return False

    def has_change_permission(self, request, obj=None):
        """Las categorías no se editan a mano."""
        return False


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    """Consulta de los presupuestos mensuales."""

    list_display = ['id', 'user_id', 'category', 'period', 'currency', 'limit_amount']
    list_filter = ['period', 'currency', 'category']
    readonly_fields = [
        'id',
        'user_id',
        'category',
        'period',
        'limit_amount',
        'currency',
        'alert_threshold',
        'created_at',
        'updated_at',
    ]

    def has_add_permission(self, request):
        """Los presupuestos se crean únicamente desde los servicios de budgets."""
        return False

    def has_change_permission(self, request, obj=None):
        """Los presupuestos no se editan a mano."""
        return False
