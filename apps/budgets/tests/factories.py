"""Factories de la app budgets."""

import uuid
from decimal import Decimal

import factory

from apps.budgets.models import Budget, Category, Expense


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


class ExpenseFactory(factory.django.DjangoModelFactory):
    """Factory de Expense."""

    class Meta:
        model = Expense

    user_id = factory.LazyFunction(uuid.uuid4)
    category = factory.SubFactory(CategoryFactory)
    ledger_transaction_id = factory.LazyFunction(uuid.uuid4)


def create_approved_user(email: str = 'budgets@example.com'):
    """Crea un usuario con KYC aprobada usando los servicios de identity."""
    from apps.identity.services import register_user, resolve_kyc, submit_kyc

    user = register_user(email=email, password='TestPass123!')
    verification = submit_kyc(user=user, documents={})
    resolve_kyc(
        verification_id=verification.id,
        status='approved',
        resolved_by_user_id=uuid.uuid4(),
    )
    return user
