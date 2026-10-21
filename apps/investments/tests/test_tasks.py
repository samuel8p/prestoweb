"""Tests de las tareas Celery de investments.

La tarea es un adaptador delgado sobre
`services.settle_matured_positions`: la regla de negocio (pago de capital e
interés, idempotencia) vive en el service y la task solo la dispara
(AGENTS §5.1).
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.investments.tests.factories import InvestmentProductFactory, create_approved_user

pytestmark = pytest.mark.django_db


def fund_user(user_id, amount='10000.00', currency='ARS', key='fund'):
    """Deposita fondos simulados en la billetera del usuario."""
    from apps.ledger.services import deposit

    return deposit(
        user_id=user_id,
        currency=currency,
        amount=Decimal(amount),
        idempotency_key=key,
    )


def open_position_for_task(email_suffix='task', term_days=365):
    """Abre una posición de plazo fijo financiada por el usuario."""
    from apps.investments.services import open_position

    user = create_approved_user(email=f'inversor-{email_suffix}@example.com')
    product = InvestmentProductFactory(
        term_days=term_days,
        annual_rate_tna=Decimal('12.00'),
        min_amount=Decimal('1000.00'),
    )
    fund_user(user.id, key=f'fund-{email_suffix}')

    return open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key=f'open-{email_suffix}',
    )


def test_settle_investments_task_is_registered_with_its_name():
    """La task se registra con el nombre que usa el beat schedule."""
    from apps.investments.tasks import settle_investments

    assert settle_investments.name == 'apps.investments.tasks.settle_investments'


def test_settle_investments_task_is_discovered_by_the_celery_app():
    """El descubrimiento automático registra la task de la app de investments."""
    from config.celery import app

    assert 'apps.investments.tasks.settle_investments' in app.tasks


def test_settle_investments_task_pays_capital_and_interest():
    """La task liquida la posición vencida y paga capital e interés."""
    from apps.investments.models import Position
    from apps.investments.tasks import settle_investments
    from apps.ledger.selectors import get_user_wallet

    position = open_position_for_task(email_suffix='liquidada')

    settled = settle_investments(today=date(2030, 1, 1))

    position.refresh_from_db()
    wallet = get_user_wallet(user_id=position.user_id, currency='ARS')
    assert settled == 1
    assert position.status == Position.Status.MATURED
    assert wallet.balance == Decimal('10600.00')


def test_settle_investments_task_is_idempotent():
    """Liquidar dos veces no duplica el pago."""
    from apps.investments.tasks import settle_investments
    from apps.ledger.selectors import get_user_wallet

    position = open_position_for_task(email_suffix='idem')

    first = settle_investments(today=date(2030, 1, 1))
    second = settle_investments(today=date(2030, 1, 1))

    wallet = get_user_wallet(user_id=position.user_id, currency='ARS')
    assert first == 1
    assert second == 0
    assert wallet.balance == Decimal('10600.00')


def test_settle_investments_task_ignores_positions_not_matured():
    """Una posición que no venció no se liquida."""
    from apps.investments.models import Position
    from apps.investments.tasks import settle_investments
    from apps.ledger.selectors import get_user_wallet

    position = open_position_for_task(email_suffix='futura', term_days=3650)

    settled = settle_investments(today=date(2030, 1, 1))

    position.refresh_from_db()
    wallet = get_user_wallet(user_id=position.user_id, currency='ARS')
    assert settled == 0
    assert position.status == Position.Status.ACTIVE
    assert wallet.balance == Decimal('5000.00')


def test_settle_investments_task_runs_as_a_celery_task():
    """La task se puede ejecutar como tarea Celery (`.apply()`), no solo como función."""
    from apps.investments.tasks import settle_investments

    open_position_for_task(email_suffix='apply')

    result = settle_investments.apply(kwargs={'today': date(2030, 1, 1)})

    assert result.successful()
    assert result.get() == 1
