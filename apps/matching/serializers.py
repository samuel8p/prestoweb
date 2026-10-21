"""Serializers de la app matching: solo validan entrada y dan formato a la salida.

`matching` no importa `offers.models`: los serializers son planos y el
formateo vive en los selectores de la app.
"""

from rest_framework import serializers

CURRENCY_CHOICES = ['ARS', 'USD']
ORDERING_CHOICES = ['rate', 'term', 'amount']


class SearchOffersQuerySerializer(serializers.Serializer):
    """Filtros de la búsqueda de ofertas."""

    currency = serializers.ChoiceField(choices=CURRENCY_CHOICES, required=False)
    amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=0,
        required=False,
    )
    max_rate = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=0,
        required=False,
    )
    term_months = serializers.IntegerField(min_value=1, required=False)
    ordering = serializers.ChoiceField(choices=ORDERING_CHOICES, required=False)


class OfferMatchSerializer(serializers.Serializer):
    """Oferta que coincide con la búsqueda."""

    id = serializers.UUIDField()
    lender_user_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency = serializers.CharField()
    interest_rate = serializers.DecimalField(max_digits=6, decimal_places=2)
    term_months = serializers.IntegerField()
    requirements = serializers.CharField()


class OfferComparisonSerializer(OfferMatchSerializer):
    """Oferta comparada con su cuota, interés total y costo total."""

    installment = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_interest = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_cost = serializers.DecimalField(max_digits=18, decimal_places=2)


class CompareOffersSerializer(serializers.Serializer):
    """Identificadores de las ofertas a comparar."""

    offer_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=2,
    )
