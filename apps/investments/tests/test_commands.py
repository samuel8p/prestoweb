"""Tests del management command `settle_investments`.

El command y la task de Celery llaman al mismo service
(`settle_matured_positions`), así que los dos caminos tienen que producir
exactamente el mismo efecto.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command

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


def create_matured_position(email_suffix='command'):
    """Abre una posición de plazo fijo y la deja vencida."""
    from apps.investments.models import Position
    from apps.investments.services import open_position

    user = create_approved_user(email=f'inversor-{email_suffix}@example.com')
    product = InvestmentProductFactory(
        term_days=365,
        annual_rate_tna=Decimal('12.00'),
        min_amount=Decimal('1000.00'),
    )
    fund_user(user.id, key=f'fund-{email_suffix}')

    position = open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key=f'open-{email_suffix}',
    )
    Position.objects.filter(pk=position.pk).update(maturity_date=date.today() - timedelta(days=1))
    return position


def test_settle_investments_command_settles_matured_positions():
    """El command liquida la posición vencida y paga capital e interés."""
    from apps.investments.models import Position
    from apps.ledger.selectors import get_user_wallet

    position = create_matured_position(email_suffix='cmd')

    call_command('settle_investments')

    position.refresh_from_db()
    wallet = get_user_wallet(user_id=position.user_id, currency='ARS')
    assert position.status == Position.Status.MATURED
    assert wallet.balance == Decimal('10600.00')


def test_settle_investments_command_and_the_celery_task_agree():
    """El command y la task liquidan igual y no pagan dos veces."""
    from apps.investments.models import Position
    from apps.ledger.selectors import get_user_wallet

    position_from_command = create_matured_position(email_suffix='cmd-igual')
    call_command('settle_investments')

    position_from_task = create_matured_position(email_suffix='task-igual')

    from apps.investments.tasks import settle_investments

    settled = settle_investments(today=date.today())

    for position in (position_from_command, position_from_task):
        position.refresh_from_db()
        wallet = get_user_wallet(user_id=position.user_id, currency='ARS')
        assert position.status == Position.Status.MATURED
        assert wallet.balance == Decimal('10600.00')
    assert settled == 1
