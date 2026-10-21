"""Vistas de la API de reports.

Las vistas son finas: validan los parámetros, llaman a los selectores y
devuelven la respuesta. La agregación vive en `selectors.py` y la exportación
a CSV en `export.py`.
"""

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination
from apps.reports import export
from apps.reports.exceptions import InvalidReportParameters, ReportTooLarge
from apps.reports.selectors import (
    build_loan_summary_rows,
    build_movement_rows,
    get_investments_report,
    get_loans_report,
    get_spending_report,
    list_movements_for_report,
    parse_currency,
    parse_period,
)
from apps.reports.serializers import (
    InvestmentPositionSerializer,
    InvestmentsReportSerializer,
    LoansReportSerializer,
    MovementReportRowSerializer,
    SpendingCategorySerializer,
    SpendingReportSerializer,
)

# Columnas del CSV de préstamos: el reporte tiene dos roles y no una lista plana.
LOAN_SUMMARY_COLUMNS = (
    'role',
    'active_loans',
    'outstanding_amount',
    'interest_amount',
    'next_installments',
)


def wants_csv(request) -> bool:
    """True si el pedido pide la exportación a CSV.

    Args:
        request: la petición HTTP.

    Returns:
        True si hay que exportar a CSV.

    Raises:
        ValidationError: si el valor de `export` no es `csv`.
    """
    requested = request.query_params.get('export')
    if not requested:
        return False
    if requested != 'csv':
        raise ValidationError({'detail': ['El valor del parámetro export debe ser csv.']})
    return True


def csv_response(rows, columns, filename) -> Response:
    """Arma la respuesta CSV de un reporte.

    Args:
        rows: filas del reporte.
        columns: columnas, en orden.
        filename: nombre del archivo descargable.

    Returns:
        La respuesta HTTP con el CSV.

    Raises:
        ValidationError: si el reporte supera el tope de filas exportables.
    """
    try:
        return export.render_csv(rows, columns, filename)
    except ReportTooLarge as exc:
        raise ValidationError({'detail': [str(exc)]}) from exc


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
            as_csv = wants_csv(request)
        except InvalidReportParameters as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        report = get_spending_report(
            user_id=request.user.id,
            currency=currency,
            period=period,
        )
        if as_csv:
            columns = list(SpendingCategorySerializer().fields)
            return csv_response(report['categories'], columns, 'reporte-gasto.csv')
        return Response(SpendingReportSerializer(report).data)


class LoansReportView(APIView):
    """Préstamos del usuario como prestatario y como prestamista."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: LoansReportSerializer},
        summary='Ver el resumen de préstamos',
        operation_id='reports_loans',
    )
    def get(self, request):
        """Devuelve el resumen de los préstamos del usuario en la moneda pedida."""
        try:
            currency = parse_currency(request.query_params)
            as_csv = wants_csv(request)
        except InvalidReportParameters as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        report = get_loans_report(user_id=request.user.id, currency=currency)
        if as_csv:
            rows = build_loan_summary_rows(report)
            return csv_response(rows, LOAN_SUMMARY_COLUMNS, 'reporte-prestamos.csv')
        return Response(LoansReportSerializer(report).data)


class InvestmentsReportView(APIView):
    """Posiciones de inversión del usuario."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: InvestmentsReportSerializer},
        summary='Ver el resumen de inversiones',
        operation_id='reports_investments',
    )
    def get(self, request):
        """Devuelve el resumen de las posiciones de inversión del usuario."""
        try:
            currency = parse_currency(request.query_params)
            as_csv = wants_csv(request)
        except InvalidReportParameters as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        report = get_investments_report(user_id=request.user.id, currency=currency)
        if as_csv:
            columns = list(InvestmentPositionSerializer().fields)
            return csv_response(report['positions'], columns, 'reporte-inversiones.csv')
        return Response(InvestmentsReportSerializer(report).data)


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
            as_csv = wants_csv(request)
        except InvalidReportParameters as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        movements = list_movements_for_report(
            user_id=request.user.id,
            currency=currency,
            period=period,
        )
        if as_csv:
            rows = build_movement_rows(movements[: export.MAX_EXPORT_ROWS + 1])
            columns = list(MovementReportRowSerializer().fields)
            return csv_response(rows, columns, 'reporte-movimientos.csv')
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(movements, request, view=self)
        rows = build_movement_rows(page)
        return paginator.get_paginated_response(MovementReportRowSerializer(rows, many=True).data)
