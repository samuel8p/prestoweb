"""Serializers de la app offers: solo validan entrada y dan formato a la salida."""

from rest_framework import serializers

from apps.offers.models import Offer


class OfferSerializer(serializers.ModelSerializer):
    """Datos de una oferta de préstamo."""

    class Meta:
        model = Offer
        fields = [
            'id',
            'lender_user_id',
            'amount',
            'currency',
            'interest_rate',
            'term_months',
            'requirements',
            'status',
            'created_at',
        ]
        read_only_fields = fields


class CreateOfferSerializer(serializers.Serializer):
    """Datos para publicar una oferta."""

    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=0)
    currency = serializers.ChoiceField(choices=Offer.Currency.choices)
    interest_rate = serializers.DecimalField(max_digits=6, decimal_places=2, min_value=0)
    term_months = serializers.IntegerField(min_value=1)
    requirements = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class UpdateOfferSerializer(serializers.Serializer):
    """Datos que el prestamista puede modificar en su oferta."""

    amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=0,
        required=False,
    )
    currency = serializers.ChoiceField(choices=Offer.Currency.choices, required=False)
    interest_rate = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=0,
        required=False,
    )
    term_months = serializers.IntegerField(min_value=1, required=False)
    requirements = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
    )
    status = serializers.ChoiceField(
        choices=[Offer.Status.EXPIRED],
        required=False,
    )
