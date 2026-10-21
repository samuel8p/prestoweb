"""Tests de la alerta de presupuesto que se dispara al categorizar un movimiento."""

from decimal import Decimal

import pytest

from apps.budgets.tests.factories import create_approved_user

pytestmark = pytest.mark.django_db


def create_category(user, name='Comida'):
    """Crea una categoría de gasto del usuario."""
    from apps.budgets.services import create_category as service_create

    return service_create(user_id=user.id, name=name)


def create_budget(user, category, limit='100.00', threshold=50):
    """Crea un presupuesto mensual para la categoría."""
    from apps.budgets.services import create_budget as service_create

    return service_create(
        user_id=user.id,
        category_id=category.id,
        limit_amount=Decimal(limit),
        currency='ARS',
        alert_threshold=threshold,
    )


def make_withdrawal(user_id, amount='60.00', key='alerta'):
    """Retira fondos de la billetera del usuario."""
    from apps.ledger.services import withdraw

    return withdraw(
        user_id=user_id,
        currency='ARS',
        amount=Decimal(amount),
        idempotency_key=key,
    )


def test_categorizing_a_movement_emits_the_alert_signal():
    """Al cruzar el umbral se emite la señal de alerta del presupuesto."""
    from apps.budgets import signals
    from apps.budgets.services import categorize_movement
    from apps.ledger.services import deposit

    user = create_approved_user(email='alerta-presupuesto@example.com')
    category = create_category(user)
    create_budget(user, category)
    deposit(
        user_id=user.id,
        currency='ARS',
        amount=Decimal('1000.00'),
        idempotency_key='alerta-fondo',
    )
    movement = make_withdrawal(user.id, amount='60.00', key='alerta-gasto')
    received = []

    def receiver(sender, **kwargs):
        received.append(kwargs)

    signals.budget_alert.connect(receiver)
    try:
        categorize_movement(
            user_id=user.id,
            ledger_transaction_id=movement.id,
            category_id=category.id,
        )
    finally:
        signals.budget_alert.disconnect(receiver)

    assert len(received) == 1
    assert received[0]['user_id'] == user.id
    assert received[0]['reference_id']


def test_categorizing_a_movement_below_the_threshold_does_not_alert():
    """Si el gasto no llega al umbral no hay alerta."""
    from apps.budgets import signals
    from apps.budgets.services import categorize_movement
    from apps.ledger.services import deposit

    user = create_approved_user(email='alerta-bajo@example.com')
    category = create_category(user)
    create_budget(user, category, limit='100.00', threshold=80)
    deposit(
        user_id=user.id,
        currency='ARS',
        amount=Decimal('1000.00'),
        idempotency_key='alerta-bajo-fondo',
    )
    movement = make_withdrawal(user.id, amount='10.00', key='alerta-bajo-gasto')
    received = []

    def receiver(sender, **kwargs):
        received.append(kwargs)

    signals.budget_alert.connect(receiver)
    try:
        categorize_movement(
            user_id=user.id,
            ledger_transaction_id=movement.id,
            category_id=category.id,
        )
    finally:
        signals.budget_alert.disconnect(receiver)

    assert received == []


def test_the_alert_reference_is_the_same_for_the_same_budget_and_month():
    """El identificador de la alerta se deriva del presupuesto y del mes."""
    from apps.budgets.selectors import budget_alert_reference

    budget_id = '33333333-3333-3333-3333-333333333333'

    first = budget_alert_reference(budget_id=budget_id, year=2026, month=10)
    second = budget_alert_reference(budget_id=budget_id, year=2026, month=10)
    other_month = budget_alert_reference(budget_id=budget_id, year=2026, month=11)

    assert first == second
    assert first != other_month


def test_categorizing_a_movement_alerts_once_per_budget_and_month():
    """Dos categorizaciones del mismo mes avisan con el mismo identificador."""
    from apps.budgets import signals
    from apps.budgets.services import categorize_movement
    from apps.ledger.services import deposit

    user = create_approved_user(email='alerta-unica@example.com')
    category = create_category(user)
    create_budget(user, category)
    deposit(
        user_id=user.id,
        currency='ARS',
        amount=Decimal('1000.00'),
        idempotency_key='alerta-unica-fondo',
    )
    first = make_withdrawal(user.id, amount='60.00', key='alerta-unica-a')
    second = make_withdrawal(user.id, amount='20.00', key='alerta-unica-b')
    received = []

    def receiver(sender, **kwargs):
        received.append(kwargs)

    signals.budget_alert.connect(receiver)
    try:
        for movement in (first, second):
            categorize_movement(
                user_id=user.id,
                ledger_transaction_id=movement.id,
                category_id=category.id,
            )
    finally:
        signals.budget_alert.disconnect(receiver)

    assert len(received) == 2
    assert received[0]['reference_id'] == received[1]['reference_id']
