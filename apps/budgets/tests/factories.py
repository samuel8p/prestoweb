"""Factories de la app budgets."""

import uuid
from decimal import Decimal

import factory

from apps.budgets.models import Budget, Category


class CategoryFactory(factory.django.DjangoModelFactory):
    """Factory de Category."""

    class Meta:
        model = Category

    user_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f'Categoría {n}')


class BudgetFactory(factory.django.DjangoModelFactory):
    """Factory de Budget."""

    class Meta:
        model = Budget

    user_id = factory.LazyFunction(uuid.uuid4)
    category = factory.SubFactory(CategoryFactory)
    period = Budget.Period.MONTHLY
    limit_amount = Decimal('10000.00')
    currency = Budget.Currency.ARS
    alert_threshold = 80
