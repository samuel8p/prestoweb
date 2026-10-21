"""Tests de los selectores de lectura de la app budgets."""

import pytest

from apps.budgets.tests.factories import BudgetFactory, CategoryFactory

pytestmark = pytest.mark.django_db


def test_list_categories_for_user_returns_only_own_categories():
    """Cada usuario ve solo sus categorías."""
    from apps.budgets.selectors import list_categories_for_user

    user_id = '11111111-1111-1111-1111-111111111111'
    CategoryFactory(user_id=user_id, name='Comida')
    CategoryFactory(user_id='22222222-2222-2222-2222-222222222222', name='Transporte')

    categories = list_categories_for_user(user_id=user_id)

    assert [category.name for category in categories] == ['Comida']


def test_get_category_for_user_returns_none_for_another_user():
    """Una categoría ajena no se expone."""
    from apps.budgets.selectors import get_category_for_user

    category = CategoryFactory()

    assert (
        get_category_for_user(
            category_id=category.id, user_id='33333333-3333-3333-3333-333333333333'
        )
        is None
    )


def test_list_budgets_for_user_returns_only_own_budgets():
    """Cada usuario ve solo sus presupuestos."""
    from apps.budgets.selectors import list_budgets_for_user

    user_id = '11111111-1111-1111-1111-111111111111'
    BudgetFactory(user_id=user_id)
    BudgetFactory(user_id='22222222-2222-2222-2222-222222222222')

    budgets = list_budgets_for_user(user_id=user_id)

    assert len(budgets) == 1
    assert str(budgets[0].user_id) == user_id


def test_get_budget_for_user_returns_none_for_another_user():
    """Un presupuesto ajeno no se expone."""
    from apps.budgets.selectors import get_budget_for_user

    budget = BudgetFactory()

    assert (
        get_budget_for_user(budget_id=budget.id, user_id='33333333-3333-3333-3333-333333333333')
        is None
    )
