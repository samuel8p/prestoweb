"""Vistas de la API de budgets.

Las vistas son finas: validan la entrada, llaman a los services o selectors y
devuelven la respuesta. El aislamiento por usuario vive en los selectors y en
los services.
"""

from datetime import UTC, datetime

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.budgets.exceptions import (
    AlreadyCategorized,
    BudgetNotFound,
    CategoryNotFound,
    DuplicateBudget,
    DuplicateBudgetConflict,
    DuplicateCategory,
    DuplicateCategoryConflict,
    InvalidBudget,
    InvalidCategory,
    MovementAlreadyCategorized,
    MovementNotFound,
    NotAnExpense,
)
from apps.budgets.selectors import (
    get_budget_for_user,
    get_budget_status,
    get_category_for_user,
    list_budgets_for_user,
    list_categories_for_user,
    list_expenses_for_user,
)
from apps.budgets.serializers import (
    BudgetSerializer,
    BudgetStatusSerializer,
    CategorySerializer,
    CreateBudgetSerializer,
    CreateCategorySerializer,
    CreateExpenseSerializer,
    ExpenseSerializer,
)
from apps.budgets.services import categorize_movement, create_budget, create_category
from apps.core.pagination import StandardPagination


class CategoryListCreateView(APIView):
    """Categorías de gasto del usuario autenticado."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        responses={200: CategorySerializer},
        summary='Listar las categorías propias',
        operation_id='budgets_categories_list',
    )
    def get(self, request):
        """Lista las categorías de gasto del usuario."""
        categories = list_categories_for_user(user_id=request.user.id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(categories, request, view=self)
        return paginator.get_paginated_response(CategorySerializer(page, many=True).data)

    @extend_schema(
        request=CreateCategorySerializer,
        responses={201: CategorySerializer},
        summary='Crear una categoría de gasto',
        operation_id='budgets_categories_create',
    )
    def post(self, request):
        """Crea una categoría de gasto para el usuario."""
        serializer = CreateCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            category = create_category(
                user_id=request.user.id,
                name=serializer.validated_data['name'],
            )
        except InvalidCategory as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        except DuplicateCategory as exc:
            raise DuplicateCategoryConflict(str(exc)) from exc
        return Response(CategorySerializer(category).data, status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    """Detalle de una categoría propia."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: CategorySerializer},
        summary='Ver una categoría propia',
        operation_id='budgets_categories_retrieve',
    )
    def get(self, request, category_id):
        """Devuelve la categoría del usuario."""
        category = get_category_for_user(category_id=category_id, user_id=request.user.id)
        if category is None:
            raise NotFound('La categoría no existe.')
        return Response(CategorySerializer(category).data, status=status.HTTP_200_OK)


class BudgetListCreateView(APIView):
    """Presupuestos mensuales del usuario autenticado."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        responses={200: BudgetSerializer},
        summary='Listar los presupuestos propios',
        operation_id='budgets_list',
    )
    def get(self, request):
        """Lista los presupuestos del usuario."""
        budgets = list_budgets_for_user(user_id=request.user.id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(budgets, request, view=self)
        return paginator.get_paginated_response(BudgetSerializer(page, many=True).data)

    @extend_schema(
        request=CreateBudgetSerializer,
        responses={201: BudgetSerializer},
        summary='Crear un presupuesto mensual',
        operation_id='budgets_create',
    )
    def post(self, request):
        """Crea el presupuesto mensual de una categoría y moneda."""
        serializer = CreateBudgetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            budget = create_budget(
                user_id=request.user.id,
                category_id=data['category_id'],
                limit_amount=data['limit_amount'],
                currency=data['currency'],
                alert_threshold=data['alert_threshold'],
            )
        except CategoryNotFound as exc:
            raise NotFound(str(exc)) from exc
        except InvalidBudget as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        except DuplicateBudget as exc:
            raise DuplicateBudgetConflict(str(exc)) from exc
        return Response(BudgetSerializer(budget).data, status=status.HTTP_201_CREATED)


class BudgetDetailView(APIView):
    """Detalle de un presupuesto propio."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: BudgetSerializer},
        summary='Ver un presupuesto propio',
        operation_id='budgets_retrieve',
    )
    def get(self, request, budget_id):
        """Devuelve el presupuesto del usuario."""
        budget = get_budget_for_user(budget_id=budget_id, user_id=request.user.id)
        if budget is None:
            raise NotFound('El presupuesto no existe.')
        return Response(BudgetSerializer(budget).data, status=status.HTTP_200_OK)


class BudgetStatusView(APIView):
    """Estado de un presupuesto en un período."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: BudgetStatusSerializer},
        summary='Ver el estado del presupuesto',
        operation_id='budgets_status',
    )
    def get(self, request, budget_id):
        """Devuelve el gastado, el límite y la alerta del presupuesto."""
        budget = get_budget_for_user(budget_id=budget_id, user_id=request.user.id)
        if budget is None:
            raise NotFound('El presupuesto no existe.')
        now = datetime.now(UTC)
        year = _parse_period_value(request.query_params.get('year'), now.year)
        month = _parse_period_value(request.query_params.get('month'), now.month)
        if not 1 <= month <= 12:
            raise ValidationError({'detail': ['El mes debe estar entre 1 y 12.']})
        status_data = get_budget_status(budget=budget, year=year, month=month)
        return Response(BudgetStatusSerializer(status_data).data, status=status.HTTP_200_OK)


class ExpenseListCreateView(APIView):
    """Gastos categorizados del usuario autenticado."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        responses={200: ExpenseSerializer},
        summary='Listar los gastos propios',
        operation_id='budgets_expenses_list',
    )
    def get(self, request):
        """Lista los gastos categorizados del usuario."""
        expenses = list_expenses_for_user(user_id=request.user.id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(expenses, request, view=self)
        return paginator.get_paginated_response(ExpenseSerializer(page, many=True).data)

    @extend_schema(
        request=CreateExpenseSerializer,
        responses={201: ExpenseSerializer},
        summary='Categorizar un movimiento como gasto',
        operation_id='budgets_expenses_create',
    )
    def post(self, request):
        """Categoriza un movimiento del ledger como gasto del usuario."""
        serializer = CreateExpenseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            expense = categorize_movement(
                user_id=request.user.id,
                ledger_transaction_id=data['ledger_transaction_id'],
                category_id=data['category_id'],
            )
        except CategoryNotFound as exc:
            raise NotFound(str(exc)) from exc
        except MovementNotFound as exc:
            raise NotFound(str(exc)) from exc
        except NotAnExpense as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        except AlreadyCategorized as exc:
            raise MovementAlreadyCategorized(str(exc)) from exc
        return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)


def _parse_period_value(raw_value, default: int) -> int:
    """Convierte un parámetro de período a entero.

    Args:
        raw_value: valor crudo de la query string, o None.
        default: valor a usar si no viene el parámetro.

    Returns:
        El año o el mes pedido.

    Raises:
        ValidationError: si el valor no es un número entero.
    """
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({'detail': ['El período no es válido.']}) from exc
