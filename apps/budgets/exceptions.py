"""Excepciones de dominio de la app budgets."""

from rest_framework import status
from rest_framework.exceptions import APIException

from apps.core.exceptions import DomainError


class BudgetsError(DomainError):
    """Error de dominio de budgets."""


class CategoryNotFound(BudgetsError):
    """La categoría no existe o no es del usuario."""


class BudgetNotFound(BudgetsError):
    """El presupuesto no existe o no es del usuario."""


class InvalidCategory(BudgetsError):
    """La categoría no tiene datos válidos."""


class InvalidBudget(BudgetsError):
    """El presupuesto no tiene datos válidos."""


class DuplicateCategory(BudgetsError):
    """El usuario ya tiene una categoría con ese nombre."""


class DuplicateBudget(BudgetsError):
    """El usuario ya tiene un presupuesto para esa categoría, período y moneda."""


class MovementNotFound(BudgetsError):
    """El movimiento no existe o no es visible para el usuario."""


class NotAnExpense(BudgetsError):
    """El movimiento no cuenta como gasto del usuario."""


class AlreadyCategorized(BudgetsError):
    """El movimiento ya tiene una categoría."""


class DuplicateCategoryConflict(APIException):
    """HTTP 409: el usuario ya tiene una categoría con ese nombre."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Ya tenés una categoría con ese nombre.'
    default_code = 'duplicate_category'


class DuplicateBudgetConflict(APIException):
    """HTTP 409: ya existe ese presupuesto para la categoría, período y moneda."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Ya tenés un presupuesto para esa categoría, período y moneda.'
    default_code = 'duplicate_budget'


class MovementAlreadyCategorized(APIException):
    """HTTP 409: el movimiento ya está categorizado."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Ese movimiento ya está categorizado.'
    default_code = 'movement_already_categorized'
