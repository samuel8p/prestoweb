"""Tests del aviso que se genera al liquidar una posición de inversión."""

from datetime import date
from decimal import Decimal

import pytest

from apps.investments.tests.factories import create_approved_user

pytestmark = pytest.mark.django_db


def open_position(user, key='notif-inv'):
    """Abre una posición de plazo fijo para el usuario."""
    from apps.investments.services import open_position as service_open
    from apps.investments.tests.factories import InvestmentProductFactory
    from apps.ledger.services import deposit

    product = InvestmentProductFactory(
        term_days=365,
        annual_rate_tna=Decimal('12.00'),
        min_amount=Decimal('1000.00'),
    )
    deposit(
        user_id=user.id,
        currency='ARS',
        amount=Decimal('10000.00'),
        idempotency_key=f'{key}-fondos',
    )
    return service_open(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key=f'{key}-apertura',
    )


def test_settling_a_position_emits_the_signal():
    """La liquidación emite la señal con el inversionista y la posición."""
    from apps.investments.services import settle_matured_positions
    from apps.investments.signals import investment_settled

    user = create_approved_user(email='notif-inversion@example.com')
    position = open_position(user)
    received = []

    def receiver(sender, **kwargs):
        received.append(kwargs)

    investment_settled.connect(receiver)
    try:
        settle_matured_positions(today=date(2030, 1, 1))
    finally:
        investment_settled.disconnect(receiver)

    assert len(received) == 1
    assert received[0]['user_id'] == user.id
    assert received[0]['reference_id'] == position.id


def test_settling_a_position_creates_the_notification_and_sends_the_email(
    django_capture_on_commit_callbacks,
):
    """La liquidación deja el aviso enviado y el email en la bandeja."""
    from django.core import mail

    from apps.investments.services import settle_matured_positions
    from apps.notifications.models import Notification

    user = create_approved_user(email='notif-inversion-email@example.com')
    position = open_position(user, key='notif-inv-2')
    mail.outbox.clear()

    with django_capture_on_commit_callbacks(execute=True):
        settle_matured_positions(today=date(2030, 1, 1))

    notification = Notification.objects.get(
        user_id=user.id,
        event_type=Notification.EventType.INVESTMENT_SETTLED,
        reference_id=position.id,
    )
    assert notification.status == Notification.Status.SENT
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ['notif-inversion-email@example.com']
    assert 'liquidó' in mail.outbox[0].subject
