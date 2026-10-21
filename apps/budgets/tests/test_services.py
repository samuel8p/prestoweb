"""Tests de los servicios de escritura de la app budgets."""

from decimal import Decimal

import pytest

from apps.budgets.tests.factories import CategoryFactory

pytestmark = pytest.mark.django_db


def test_create_category_returns_the_new_category():
    """El servicio crea la categoría del usuario."""
    from apps.budgets.services import create_category

    user_id = '11111111-1111-1111-1111-111111111111'

    category = create_category(user_id=user_id, name='Comida')

    assert str(category.user_id) == user_id
    assert category.name == 'Comida'


def test_create_category_rejects_an_empty_name():
    """Una categoría sin nombre no se puede crear."""
    from apps.budgets.exceptions import InvalidCategory
    from apps.budgets.services import create_category

    with pytest.raises(InvalidCategory):
        create_category(user_id='11111111-1111-1111-1111-111111111111', name='   ')


def test_create_category_rejects_a_duplicate_name_for_the_same_user():
    """El usuario no puede repetir el nombre de una categoría."""
    from apps.budgets.exceptions import DuplicateCategory
    from apps.budgets.services import create_category

    user_id = '22222222-2222-2222-2222-222222222222'
    create_category(user_id=user_id, name='Comida')

    with pytest.raises(DuplicateCategory):
        create_category(user_id=user_id, name='Comida')


def test_create_budget_returns_the_new_budget():
    """El servicio crea el presupuesto mensual de la categoría."""
    from apps.budgets.services import create_budget

    category = CategoryFactory()

    budget = create_budget(
        user_id=category.user_id,
        category_id=category.id,
        limit_amount=Decimal('50000.00'),
        currency='ARS',
        alert_threshold=80,
    )

    assert budget.category_id == category.id
    assert budget.limit_amount == Decimal('50000.00')
    assert budget.currency == 'ARS'
    assert budget.period == 'monthly'


def test_create_budget_rejects_a_category_of_another_user():
    """No se puede crear un presupuesto sobre una categoría ajena."""
    from apps.budgets.exceptions import CategoryNotFound
    from apps.budgets.services import create_budget

    category = CategoryFactory()

    with pytest.raises(CategoryNotFound):
        create_budget(
            user_id='33333333-3333-3333-3333-333333333333',
            category_id=category.id,
            limit_amount=Decimal('50000.00'),
            currency='ARS',
            alert_threshold=80,
        )


def test_create_budget_rejects_a_non_positive_limit():
    """El límite del presupuesto tiene que ser mayor que cero."""
    from apps.budgets.exceptions import InvalidBudget
    from apps.budgets.services import create_budget

    category = CategoryFactory()

    with pytest.raises(InvalidBudget):
        create_budget(
            user_id=category.user_id,
            category_id=category.id,
            limit_amount=Decimal('0.00'),
            currency='ARS',
            alert_threshold=80,
        )


def test_create_budget_rejects_an_unknown_currency():
    """Solo se aceptan las monedas del proyecto."""
    from apps.budgets.exceptions import InvalidBudget
    from apps.budgets.services import create_budget

    category = CategoryFactory()

    with pytest.raises(InvalidBudget):
        create_budget(
            user_id=category.user_id,
            category_id=category.id,
            limit_amount=Decimal('50000.00'),
            currency='EUR',
            alert_threshold=80,
        )


def test_create_budget_rejects_an_alert_threshold_out_of_range():
    """El umbral de alerta es un porcentaje entre 0 y 100."""
    from apps.budgets.exceptions import InvalidBudget
    from apps.budgets.services import create_budget

    category = CategoryFactory()

    with pytest.raises(InvalidBudget):
        create_budget(
            user_id=category.user_id,
            category_id=category.id,
            limit_amount=Decimal('50000.00'),
            currency='ARS',
            alert_threshold=101,
        )


def test_create_budget_rejects_a_duplicate_budget():
    """No hay dos presupuestos iguales para el mismo usuario y categoría."""
    from apps.budgets.exceptions import DuplicateBudget
    from apps.budgets.services import create_budget

    category = CategoryFactory()
    create_budget(
        user_id=category.user_id,
        category_id=category.id,
        limit_amount=Decimal('50000.00'),
        currency='ARS',
        alert_threshold=80,
    )

    with pytest.raises(DuplicateBudget):
        create_budget(
            user_id=category.user_id,
            category_id=category.id,
            limit_amount=Decimal('60000.00'),
            currency='ARS',
            alert_threshold=90,
        )
