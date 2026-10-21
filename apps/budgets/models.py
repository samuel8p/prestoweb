"""Modelos de la app budgets: categorías de gasto y presupuestos mensuales.

La app **no guarda importes**: el monto de un gasto se deriva del ledger al
leer (ver `selectors.py`). Lo que se guarda es la clasificación del usuario:
qué categoría tiene cada movimiento.
"""

from django.db import models

from apps.core.models import BaseModel

CATEGORY_NAME_MAX_LENGTH = 100


class Category(BaseModel):
    """Categoría de gasto personal de un usuario."""

    user_id = models.UUIDField()
    name = models.CharField(max_length=CATEGORY_NAME_MAX_LENGTH)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'name'],
                name='budgets_category_name_unique_per_user',
            ),
        ]
        ordering = ['name']

    def __str__(self):
        return f'Category<{self.user_id}:{self.name}>'


class Budget(BaseModel):
    """Presupuesto mensual de gasto por categoría y moneda.

    El presupuesto evalúa **una sola moneda**: nunca se suman gastos en ARS y
    USD. El mes es el mes calendario en UTC (`TIME_ZONE` del proyecto).
    """

    class Period(models.TextChoices):
        MONTHLY = 'monthly', 'Mensual'

    class Currency(models.TextChoices):
        ARS = 'ARS', 'Peso argentino'
        USD = 'USD', 'Dólar'

    user_id = models.UUIDField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='budgets')
    period = models.CharField(max_length=8, choices=Period.choices, default=Period.MONTHLY)
    limit_amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices)
    alert_threshold = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'category', 'period', 'currency'],
                name='budgets_budget_unique_per_category_period_currency',
            ),
            models.CheckConstraint(
                condition=models.Q(limit_amount__gt=0),
                name='budgets_budget_limit_amount_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(alert_threshold__gte=0) & models.Q(alert_threshold__lte=100),
                name='budgets_budget_alert_threshold_percentage',
            ),
        ]
        ordering = ['category__name', 'currency']

    def __str__(self):
        return f'Budget<{self.category_id}:{self.currency}:{self.limit_amount}>'
