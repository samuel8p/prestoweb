"""Serializers de la app loans: solo validan entrada y dan formato a la salida."""

from rest_framework import serializers

from apps.loans.models import Installment, Loan, OfferTermsSnapshot


class OfferTermsSnapshotSerializer(serializers.ModelSerializer):
    """Snapshot inmutable de los términos de la oferta aceptada."""

    class Meta:
        model = OfferTermsSnapshot
        fields = [
            'id',
            'accepted_at',
            'accepted_by_user_id',
            'snapshot_data',
            'is_immutable',
        ]
        read_only_fields = fields


class InstallmentSerializer(serializers.ModelSerializer):
    """Cuota de un préstamo."""

    class Meta:
        model = Installment
        fields = [
            'id',
            'number',
            'due_date',
            'principal_amount',
            'interest_amount',
            'amount',
            'status',
            'paid_at',
        ]
        read_only_fields = fields


class LoanSerializer(serializers.ModelSerializer):
    """Datos de un préstamo."""

    class Meta:
        model = Loan
        fields = [
            'id',
            'borrower_user_id',
            'lender_user_id',
            'offer_id',
            'principal',
            'currency',
            'interest_rate',
            'term_months',
            'status',
            'accepted_at',
        ]
        read_only_fields = fields


class LoanDetailSerializer(LoanSerializer):
    """Préstamo con su snapshot de términos y sus cuotas."""

    terms_snapshot = OfferTermsSnapshotSerializer(read_only=True)
    installments = InstallmentSerializer(many=True, read_only=True)

    class Meta(LoanSerializer.Meta):
        fields = [
            *LoanSerializer.Meta.fields,
            'terms_snapshot',
            'installments',
        ]


class AcceptOfferSerializer(serializers.Serializer):
    """Datos para aceptar una oferta."""

    offer_id = serializers.UUIDField()
