"""Serializers de la app core."""

from rest_framework import serializers


class MetaSerializer(serializers.Serializer):
    """Información pública del modo en que corre la aplicación."""

    mode = serializers.CharField()
    simulated_money = serializers.BooleanField()
