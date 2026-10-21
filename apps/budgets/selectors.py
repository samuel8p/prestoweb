"""Selectores de lectura de la app budgets (interfaz pública).

Los selectores aíslan al usuario: nunca devuelven categorías ni presupuestos
de otro usuario.
"""

import uuid

from django.db.models import QuerySet

from apps.budgets.models import Budget, Category


def list_categories_for_user(user_id: uuid.UUID) -> QuerySet[Category]:
    """Lista las categorías de gasto del usuario.

    Args:
        user_id: identificador del usuario.

    Returns:
        QuerySet con las categorías del usuario ordenadas por nombre.
    """
    return Category.objects.filter(user_id=user_id).order_by('name')


def get_category_for_user(category_id: uuid.UUID, user_id: uuid.UUID) -> Category | None:
    """Devuelve la categoría del usuario, o None si no existe o es de otro.

    Args:
        category_id: identificador de la categoría.
        user_id: identificador del usuario propietario.

    Returns:
        La Category del usuario o None.
    """
    return Category.objects.filter(id=category_id, user_id=user_id).first()


def list_budgets_for_user(user_id: uuid.UUID) -> QuerySet[Budget]:
    """Lista los presupuestos del usuario.

    Args:
        user_id: identificador del usuario.

    Returns:
        QuerySet con los presupuestos del usuario.
    """
    return (
        Budget.objects.filter(user_id=user_id)
        .select_related('category')
        .order_by('category__name', 'currency')
    )


def get_budget_for_user(budget_id: uuid.UUID, user_id: uuid.UUID) -> Budget | None:
    """Devuelve el presupuesto del usuario, o None si no existe o es de otro.

    Args:
        budget_id: identificador del presupuesto.
        user_id: identificador del usuario propietario.

    Returns:
        El Budget del usuario o None.
    """
    return Budget.objects.filter(id=budget_id, user_id=user_id).select_related('category').first()
