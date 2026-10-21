"""Tests de los casos borde y de concurrencia de los servicios de budgets.

Los caminos de `IntegrityError` simulan la carrera real: dos peticiones que
pasan la validación y chocan en el índice único de la base.
"""

from decimal import Decimal

import pytest

from apps.budgets.tests.factories import CategoryFactory, create_approved_user

pytestmark = pytest.mark.django_db


def test_create_category_rejects_a_too_long_name():
    """El nombre de la categoría tiene un largo máximo."""
    from apps.budgets.exceptions import InvalidCategory
    from apps.budgets.models import CATEGORY_NAME_MAX_LENGTH
    from apps.budgets.services import create_category

    with pytest.raises(InvalidCategory):
        create_category(
            user_id='11111111-1111-1111-1111-111111111111',
            name='a' * (CATEGORY_NAME_MAX_LENGTH + 1),
        )


def test_create_category_translates_a_concurrent_insert_into_a_duplicate():
    """Si la base rechaza el insert por carrera, el error es de duplicado."""
    from unittest.mock import patch

    from django.db import IntegrityError

    from apps.budgets.exceptions import DuplicateCategory
    from apps.budgets.services import create_category

    with patch(
        'apps.budgets.services.Category.objects.create',
        side_effect=IntegrityError('duplicate'),
    ):
        with pytest.raises(DuplicateCategory):
            create_category(
                user_id='11111111-1111-1111-1111-111111111111',
                name='Comida',
            )


def test_create_budget_rejects_a_non_decimal_limit():
    """El límite del presupuesto tiene que ser un Decimal, nunca un float."""
    from apps.budgets.exceptions import InvalidBudget
    from apps.budgets.services import create_budget

    category = CategoryFactory()

    with pytest.raises(InvalidBudget):
        create_budget(
            user_id=category.user_id,
            category_id=category.id,
            limit_amount=1000.5,
            currency='ARS',
            alert_threshold=80,
        )


def test_create_budget_rejects_an_unknown_period():
    """El período del presupuesto tiene que ser monthly."""
    from apps.budgets.exceptions import InvalidBudget
    from apps.budgets.services import create_budget

    category = CategoryFactory()

    with pytest.raises(InvalidBudget):
        create_budget(
            user_id=category.user_id,
            category_id=category.id,
            limit_amount=Decimal('1000.00'),
            currency='ARS',
            alert_threshold=80,
            period='weekly',
        )


def test_create_budget_translates_a_concurrent_insert_into_a_duplicate():
    """Si la base rechaza el insert por carrera, el error es de duplicado."""
    from unittest.mock import patch

    from django.db import IntegrityError

    from apps.budgets.exceptions import DuplicateBudget
    from apps.budgets.services import create_budget

    category = CategoryFactory()

    with patch(
        'apps.budgets.services.Budget.objects.create',
        side_effect=IntegrityError('duplicate'),
    ):
        with pytest.raises(DuplicateBudget):
            create_budget(
                user_id=category.user_id,
                category_id=category.id,
                limit_amount=Decimal('1000.00'),
                currency='ARS',
                alert_threshold=80,
            )


def test_categorize_movement_translates_a_concurrent_insert_into_a_conflict():
    """Si la base rechaza el insert por carrera, el movimiento ya está categorizado."""
    from unittest.mock import patch

    from django.db import IntegrityError

    from apps.budgets.exceptions import AlreadyCategorized
    from apps.budgets.services import categorize_movement
    from apps.ledger.services import deposit, withdraw

    user = create_approved_user(email='concurrencia-categoria@example.com')
    category = CategoryFactory(user_id=user.id)
    deposit(
        user_id=user.id,
        currency='ARS',
        amount=Decimal('1000.00'),
        idempotency_key='concurrencia-fondo',
    )
    movement = withdraw(
        user_id=user.id,
        currency='ARS',
        amount=Decimal('100.00'),
        idempotency_key='concurrencia-gasto',
    )

    with patch(
        'apps.budgets.services.Expense.objects.create',
        side_effect=IntegrityError('duplicate'),
    ):
        with pytest.raises(AlreadyCategorized):
            categorize_movement(
                user_id=user.id,
                ledger_transaction_id=movement.id,
                category_id=category.id,
            )
