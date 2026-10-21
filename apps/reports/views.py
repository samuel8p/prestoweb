"""Vistas de la API de reports.

Las vistas son finas: validan los parámetros, llaman a los selectores y
devuelven la respuesta. La agregación vive en `selectors.py`.
"""

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination
from apps.reports.exceptions import InvalidReportParameters
from apps.reports.selectors import (
    build_movement_rows,
    get_spending_report,
    list_movements_for_report,
    parse_currency,
    parse_period,
)
from apps.reports.serializers import (
    MovementReportRowSerializer,
    SpendingReportSerializer,
)


class MovementsReportView(APIView):
    """Movimientos del ledger del usuario en un período."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        responses={200: MovementReportRowSerializer},
        summary='Ver los movimientos del usuario en el período',
        operation_id='reports_movements',
    )
    def get(self, request):
        """Devuelve los movimientos del usuario en el rango y la moneda pedidos."""
        try:
            currency = parse_currency(request.query_params)
            period = parse_period(request.query_params)
        except InvalidReportParameters as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        movements = list_movements_for_report(
            user_id=request.user.id,
            currency=currency,
            period=period,
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(movements, request, view=self)
        rows = build_movement_rows(page)
        return paginator.get_paginated_response(MovementReportRowSerializer(rows, many=True).data)


class SpendingReportView(APIView):
    """Gasto por categoría del usuario en un período."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: SpendingReportSerializer},
        summary='Ver el gasto por categoría del período',
        operation_id='reports_spending',
    )
    def get(self, request):
        """Devuelve el gasto acumulado por categoría en el rango y la moneda pedidos."""
        try:
            currency = parse_currency(request.query_params)
            period = parse_period(request.query_params)
        except InvalidReportParameters as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        report = get_spending_report(
            user_id=request.user.id,
            currency=currency,
            period=period,
        )
        return Response(SpendingReportSerializer(report).data)
