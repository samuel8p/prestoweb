"""Serializers de la app ledger: solo validan entrada y dan formato a la salida."""

from rest_framework import serializers

from apps.ledger.models import Account, LedgerTransaction


class AccountSerializer(serializers.ModelSerializer):
    """Datos de una cuenta y su saldo."""

    class Meta:
        model = Account
        fields = ['id', 'user_id', 'currency', 'kind', 'balance', 'created_at']
        read_only_fields = fields


class CreateAccountSerializer(serializers.Serializer):
    """Datos para crear la billetera del usuario en una moneda."""

    currency = serializers.ChoiceField(choices=Account.Currency.choices)


class LedgerTransactionSerializer(serializers.ModelSerializer):
    """Datos de una transacción del libro mayor."""

    class Meta:
        model = LedgerTransaction
        fields = [
            'id',
            'type',
            'idempotency_key',
            'created_by_user_id',
            'destination_account_id',
            'occurred_at',
            'description',
            'reverses',
            'created_at',
        ]
        read_only_fields = fields


class LedgerTransactionListSerializer(serializers.ModelSerializer):
    """Un movimiento del listado, con el importe y la moneda del usuario.

    El importe y la moneda los calcula `ledger.selectors.list_user_movement_amounts`
    y llegan en el contexto (`amounts`): el serializer solo los da forma.
    """

    amount = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()

    class Meta:
        model = LedgerTransaction
        fields = [
            'id',
            'type',
            'idempotency_key',
            'created_by_user_id',
            'destination_account_id',
            'occurred_at',
            'description',
            'reverses',
            'created_at',
            'amount',
            'currency',
        ]
        read_only_fields = fields

    def get_amount(self, obj) -> str | None:
        """El importe del movimiento para el usuario, como string decimal."""
        values = self.context.get('amounts', {}).get(obj.id)
        return str(values['amount']) if values else None

    def get_currency(self, obj) -> str | None:
        """La moneda del movimiento."""
        values = self.context.get('amounts', {}).get(obj.id)
        return values['currency'] if values else None


class CreateTransactionSerializer(serializers.Serializer):
    """Datos para crear un movimiento de dinero."""

    type = serializers.ChoiceField(
        choices=[
            LedgerTransaction.Type.DEPOSIT,
            LedgerTransaction.Type.WITHDRAWAL,
            LedgerTransaction.Type.TRANSFER,
        ]
    )
    currency = serializers.ChoiceField(choices=Account.Currency.choices)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    destination_account_id = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, max_length=255)


class BalanceSerializer(serializers.Serializer):
    """Saldo de una cuenta."""

    account_id = serializers.UUIDField()
    currency = serializers.CharField()
    balance = serializers.DecimalField(max_digits=18, decimal_places=2)
