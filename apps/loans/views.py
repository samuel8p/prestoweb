"""Vistas de la API de loans."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import InsufficientFunds, KYCNotCompleted
from apps.core.openapi import IDEMPOTENCY_KEY_PARAMETER, paginated_response
from apps.core.pagination import StandardPagination
from apps.identity.permissions import KycApprovedForUnsafeMethods
from apps.ledger.exceptions import IdempotencyConflict, IdempotencyKeyConflict
from apps.loans.exceptions import (
    InstallmentAlreadyPaid,
    InstallmentOutOfOrder,
    LoanNotFound,
    NotTheBorrower,
)
from apps.loans.selectors import get_loan_for_party, list_loans_for_user
from apps.loans.serializers import (
    AcceptOfferSerializer,
    InstallmentSerializer,
    LoanDetailSerializer,
    LoanSerializer,
)
from apps.loans.services import accept_offer, pay_installment
from apps.offers.exceptions import (
    CannotAcceptOwnOffer,
    OfferNotAcceptable,
    OfferNotFound,
)


class LoanListCreateView(KycApprovedForUnsafeMethods, APIView):
    """Préstamos en los que el usuario autenticado es parte."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        responses={200: paginated_response(LoanSerializer)},
        summary='Listar los préstamos propios',
        operation_id='loans_list',
    )
    def get(self, request):
        """Lista los préstamos del usuario como prestatario o prestamista."""
        loans = list_loans_for_user(user_id=request.user.id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(loans, request, view=self)
        return paginator.get_paginated_response(LoanSerializer(page, many=True).data)

    @extend_schema(
        request=AcceptOfferSerializer,
        parameters=[IDEMPOTENCY_KEY_PARAMETER],
        responses={201: LoanSerializer},
        summary='Aceptar una oferta y recibir el préstamo',
    )
    def post(self, request):
        """Acepta una oferta y devuelve el préstamo creado."""
        serializer = AcceptOfferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            raise ValidationError(
                {'idempotency_key': ['El header Idempotency-Key es obligatorio.']}
            )
        try:
            loan = accept_offer(
                borrower_user_id=request.user.id,
                offer_id=serializer.validated_data['offer_id'],
                idempotency_key=idempotency_key,
            )
        except IdempotencyConflict as exc:
            raise IdempotencyKeyConflict() from exc
        except KYCNotCompleted as exc:
            raise PermissionDenied(str(exc)) from exc
        except InsufficientFunds as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        except (OfferNotFound, OfferNotAcceptable, CannotAcceptOwnOffer) as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        return Response(LoanSerializer(loan).data, status=status.HTTP_201_CREATED)


class LoanDetailView(APIView):
    """Detalle de un préstamo propio."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: LoanDetailSerializer},
        summary='Ver un préstamo propio con snapshot y cuotas',
        operation_id='loans_retrieve',
    )
    def get(self, request, loan_id):
        """Devuelve el préstamo con su snapshot y sus cuotas."""
        loan = get_loan_for_party(loan_id=loan_id, user_id=request.user.id)
        if loan is None:
            raise NotFound('El préstamo no existe.')
        return Response(LoanDetailSerializer(loan).data, status=status.HTTP_200_OK)


class InstallmentPayView(KycApprovedForUnsafeMethods, APIView):
    """Pago de una cuota del préstamo."""

    permission_classes = [IsAuthenticated]
    serializer_class = InstallmentSerializer

    @extend_schema(
        request=None,
        responses={200: InstallmentSerializer},
        summary='Pagar una cuota del préstamo',
    )
    def post(self, request, loan_id, number):
        """Paga la cuota indicada del préstamo."""
        if get_loan_for_party(loan_id=loan_id, user_id=request.user.id) is None:
            raise NotFound('El préstamo no existe.')
        try:
            installment = pay_installment(
                loan_id=loan_id,
                number=number,
                borrower_user_id=request.user.id,
            )
        except LoanNotFound as exc:
            raise NotFound(str(exc)) from exc
        except NotTheBorrower as exc:
            raise PermissionDenied(str(exc)) from exc
        except (InstallmentOutOfOrder, InstallmentAlreadyPaid) as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        except InsufficientFunds as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        return Response(InstallmentSerializer(installment).data, status=status.HTTP_200_OK)
