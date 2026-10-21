"""Tests de los modelos de la app budgets."""

from datetime import date
from decimal import Decimal

import pytest

from apps.budgets.tests.factories import BudgetFactory, CategoryFactory

pytestmark = pytest.mark.django_db


def test_category_belongs_to_a_user():
    """La categoría es del usuario que la crea."""
    category = CategoryFactory(user_id='11111111-1111-1111-1111-111111111111')

    assert str(category.user_id) == '11111111-1111-1111-1111-111111111111'
    assert category.name


def test_category_name_is_unique_per_user():
    """Un usuario no puede tener dos categorías con el mismo nombre."""
    from django.db import IntegrityError, transaction

    user_id = '22222222-2222-2222-2222-222222222222'
    CategoryFactory(user_id=user_id, name='Comida')

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CategoryFactory(user_id=user_id, name='Comida')


def test_two_users_can_have_the_same_category_name():
    """Cada usuario tiene su propia taxonomía de categorías."""
    CategoryFactory(user_id='33333333-3333-3333-3333-333333333333', name='Comida')
    CategoryFactory(user_id='44444444-4444-4444-4444-444444444444', name='Comida')


def test_budget_requires_a_positive_limit():
    """El límite del presupuesto tiene que ser mayor que cero."""
    from django.db import IntegrityError, transaction

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            BudgetFactory(limit_amount=Decimal('0.00'))


def test_budget_alert_threshold_must_be_between_0_and_100():
    """El umbral de alerta es un porcentaje entre 0 y 100."""
    from django.db import IntegrityError, transaction

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            BudgetFactory(alert_threshold=101)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            BudgetFactory(alert_threshold=-1)


def test_budget_is_unique_per_user_category_period_and_currency():
    """No hay dos presupuestos iguales para el mismo usuario."""
    from django.db import IntegrityError, transaction

    category = CategoryFactory()
    BudgetFactory(
        user_id=category.user_id,
        category=category,
        currency='ARS',
        limit_amount=Decimal('1000.00'),
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            BudgetFactory(
                user_id=category.user_id,
                category=category,
                currency='ARS',
                limit_amount=Decimal('2000.00'),
            )


def test_budget_allows_one_budget_per_currency_for_the_same_category():
    """La misma categoría puede tener un presupuesto en ARS y otro en USD."""
    category = CategoryFactory()
    BudgetFactory(
        user_id=category.user_id,
        category=category,
        currency='ARS',
        limit_amount=Decimal('1000.00'),
    )
    BudgetFactory(
        user_id=category.user_id,
        category=category,
        currency='USD',
        limit_amount=Decimal('300.00'),
    )

    assert category.budgets.count() == 2


def test_budget_period_is_monthly_by_default():
    """El presupuesto es mensual por defecto."""
    budget = BudgetFactory()

    assert budget.period == 'monthly'
