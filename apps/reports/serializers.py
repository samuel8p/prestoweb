"""Serializers de la app reports: solo dan formato a la salida."""

from rest_framework import serializers


class MovementReportRowSerializer(serializers.Serializer):
    """Un movimiento del ledger dentro del reporte."""

    id = serializers.UUIDField()
    type = serializers.CharField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency = serializers.CharField()
    occurred_at = serializers.DateTimeField()
    description = serializers.CharField(allow_blank=True)
    is_reversed = serializers.BooleanField()


class SpendingCategorySerializer(serializers.Serializer):
    """El gasto acumulado de una categoría en el período."""

    category_id = serializers.UUIDField()
    category_name = serializers.CharField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    movements = serializers.IntegerField()


class SpendingReportSerializer(serializers.Serializer):
    """El reporte de gasto por categoría."""

    currency = serializers.CharField()
    from_date = serializers.CharField()
    to_date = serializers.CharField()
    total = serializers.DecimalField(max_digits=18, decimal_places=2)
    categories = SpendingCategorySerializer(many=True)


class NextInstallmentSerializer(serializers.Serializer):
    """La próxima cuota a pagar de un préstamo."""

    loan_id = serializers.UUIDField()
    number = serializers.IntegerField()
    due_date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)


class LoansRoleSummarySerializer(serializers.Serializer):
    """El resumen de los préstamos del usuario en un rol."""

    active_loans = serializers.IntegerField()
    outstanding_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    interest_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    next_installments = NextInstallmentSerializer(many=True)


class LoansReportSerializer(serializers.Serializer):
    """El reporte de préstamos."""

    currency = serializers.CharField()
    as_borrower = LoansRoleSummarySerializer()
    as_lender = LoansRoleSummarySerializer()


class InvestmentPositionSerializer(serializers.Serializer):
    """Una posición de inversión dentro del reporte."""

    position_id = serializers.UUIDField()
    product_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    interest_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    status = serializers.CharField()
    opened_at = serializers.DateTimeField()
    maturity_date = serializers.DateField()


class InvestmentsReportSerializer(serializers.Serializer):
    """El reporte de inversiones."""

    currency = serializers.CharField()
    total_invested = serializers.DecimalField(max_digits=18, decimal_places=2)
    interest_expected = serializers.DecimalField(max_digits=18, decimal_places=2)
    interest_earned = serializers.DecimalField(max_digits=18, decimal_places=2)
    positions = InvestmentPositionSerializer(many=True)
