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
