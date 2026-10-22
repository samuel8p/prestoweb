"""Serializers de la app investments: solo validan entrada y dan formato a la salida."""

from rest_framework import serializers

from apps.investments.models import InvestmentProduct, Position


class InvestmentProductSerializer(serializers.ModelSerializer):
    """Datos de un producto de inversión."""

    class Meta:
        model = InvestmentProduct
        fields = [
            'id',
            'type',
            'currency',
            'term_days',
            'annual_rate_tna',
            'min_amount',
            'status',
            'created_at',
        ]
        read_only_fields = fields


class PositionSerializer(serializers.ModelSerializer):
    """Datos de una posición de inversión."""

    currency = serializers.SerializerMethodField()

    class Meta:
        model = Position
        fields = [
            'id',
            'product',
            'amount',
            'status',
            'opened_at',
            'maturity_date',
            'interest_amount',
            'currency',
        ]
        read_only_fields = fields

    def get_currency(self, obj) -> str:
        """La moneda del producto de la posición."""
        return obj.product.currency


class PositionDetailSerializer(PositionSerializer):
    """Posición de inversión con el detalle del producto."""

    product_detail = InvestmentProductSerializer(source='product', read_only=True)

    class Meta(PositionSerializer.Meta):
        fields = [
            *PositionSerializer.Meta.fields,
            'product_detail',
        ]


class OpenPositionSerializer(serializers.Serializer):
    """Datos para abrir una posición de inversión."""

    product_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=0)
    currency = serializers.CharField(required=False, allow_blank=True, max_length=3)
