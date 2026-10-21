"""Excepciones de dominio de la app budgets."""

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
