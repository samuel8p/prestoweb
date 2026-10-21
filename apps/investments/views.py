"""Vistas de la API de investments."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import InsufficientFunds, KYCNotCompleted
from apps.core.pagination import StandardPagination
from apps.investments.exceptions import (
    InsufficientInvestmentAmount,
    ProductNotActive,
    ProductNotFound,
)
from apps.investments.selectors import (
    get_position_for_user,
    list_active_products,
    list_positions_for_user,
)
from apps.investments.serializers import (
    InvestmentProductSerializer,
    OpenPositionSerializer,
    PositionDetailSerializer,
    PositionSerializer,
)
from apps.investments.services import open_position
from apps.ledger.exceptions import CurrencyMismatch, IdempotencyConflict, IdempotencyKeyConflict


class InvestmentProductListView(APIView):
    """Productos de inversión activos del marketplace."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        responses={200: InvestmentProductSerializer},
        summary='Listar los productos de inversión activos',
    )
    def get(self, request):
        """Lista los productos de inversión disponibles."""
        products = list_active_products()
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(products, request, view=self)
        return paginator.get_paginated_response(InvestmentProductSerializer(page, many=True).data)


class PositionListCreateView(APIView):
    """Posiciones de inversión del usuario autenticado."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        responses={200: PositionSerializer},
        summary='Listar las posiciones propias',
    )
    def get(self, request):
        """Lista las posiciones de inversión del usuario."""
        positions = list_positions_for_user(user_id=request.user.id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(positions, request, view=self)
        return paginator.get_paginated_response(PositionSerializer(page, many=True).data)

    @extend_schema(
        request=OpenPositionSerializer,
        responses={201: PositionSerializer},
        summary='Abrir una inversión a plazo fijo',
    )
    def post(self, request):
        """Abre una posición de inversión a plazo fijo."""
        serializer = OpenPositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            raise ValidationError(
                {'idempotency_key': ['El header Idempotency-Key es obligatorio.']}
            )
        data = serializer.validated_data
        try:
            position = open_position(
                user_id=request.user.id,
                product_id=data['product_id'],
                amount=data['amount'],
                idempotency_key=idempotency_key,
                currency=data.get('currency') or None,
            )
        except IdempotencyConflict as exc:
            raise IdempotencyKeyConflict() from exc
        except KYCNotCompleted as exc:
            raise PermissionDenied(str(exc)) from exc
        except InsufficientFunds as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        except (ProductNotFound, ProductNotActive, InsufficientInvestmentAmount) as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        except CurrencyMismatch as exc:
            raise ValidationError({'currency': [str(exc)]}) from exc
        return Response(PositionSerializer(position).data, status=status.HTTP_201_CREATED)


class PositionDetailView(APIView):
    """Detalle de una posición de inversión propia."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: PositionDetailSerializer},
        summary='Ver una posición de inversión propia',
    )
    def get(self, request, position_id):
        """Devuelve la posición del usuario con el detalle del producto."""
        position = get_position_for_user(
            position_id=position_id,
            user_id=request.user.id,
        )
        if position is None:
            raise NotFound('La posición no existe.')
        return Response(PositionDetailSerializer(position).data, status=status.HTTP_200_OK)
