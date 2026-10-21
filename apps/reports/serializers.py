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
