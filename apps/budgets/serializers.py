"""Serializers de la app budgets: solo validan entrada y dan formato a la salida."""

from rest_framework import serializers

from apps.budgets.models import Budget, Category, Expense


class CategorySerializer(serializers.ModelSerializer):
    """Categoría de gasto del usuario."""

    class Meta:
        model = Category
        fields = ['id', 'name', 'created_at']
        read_only_fields = fields


class CreateCategorySerializer(serializers.Serializer):
    """Datos para crear una categoría de gasto."""

    name = serializers.CharField(max_length=100)


class BudgetSerializer(serializers.ModelSerializer):
    """Presupuesto mensual de una categoría."""

    category = CategorySerializer(read_only=True)

    class Meta:
        model = Budget
        fields = [
            'id',
            'category',
            'period',
            'limit_amount',
            'currency',
            'alert_threshold',
            'created_at',
        ]
        read_only_fields = fields


class CreateBudgetSerializer(serializers.Serializer):
    """Datos para crear un presupuesto."""

    category_id = serializers.UUIDField()
    limit_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency = serializers.ChoiceField(choices=Budget.Currency.choices)
    alert_threshold = serializers.IntegerField(min_value=0, max_value=100)


class ExpenseSerializer(serializers.ModelSerializer):
    """Gasto personal: un movimiento del ledger con su categoría."""

    category = CategorySerializer(read_only=True)

    class Meta:
        model = Expense
        fields = ['id', 'category', 'ledger_transaction_id', 'created_at']
        read_only_fields = fields


class CreateExpenseSerializer(serializers.Serializer):
    """Datos para categorizar un movimiento del ledger como gasto."""

    category_id = serializers.UUIDField()
    ledger_transaction_id = serializers.UUIDField()


class BudgetStatusSerializer(serializers.Serializer):
    """Estado del presupuesto en un período."""

    budget_id = serializers.UUIDField()
    category_id = serializers.UUIDField()
    period = serializers.CharField()
    currency = serializers.CharField()
    year = serializers.IntegerField()
    month = serializers.IntegerField()
    limit_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    spent_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    remaining_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    threshold_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    alert_triggered = serializers.BooleanField()
