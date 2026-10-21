"""Tests de los receptores de señales de las apps emisoras."""

import uuid

import pytest
from django.core import mail
from django.test import override_settings

from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db

USER_ID = uuid.UUID('11111111-1111-1111-1111-111111111111')
REFERENCE_ID = uuid.UUID('22222222-2222-2222-2222-222222222222')


def test_receiver_creates_the_notification():
    """El receptor crea el aviso del evento."""
    from apps.notifications.receivers import handle_installment_due_soon

    handle_installment_due_soon(
        sender=None,
        user_id=USER_ID,
        reference_id=REFERENCE_ID,
    )

    notification = Notification.objects.get(
        user_id=USER_ID,
        event_type=Notification.EventType.INSTALLMENT_DUE_SOON,
        reference_id=REFERENCE_ID,
    )
    assert notification.status == Notification.Status.PENDING


def test_receiver_is_idempotent():
    """Dos ejecuciones del receptor dejan un solo aviso."""
    from apps.notifications.receivers import handle_installment_due_soon

    handle_installment_due_soon(sender=None, user_id=USER_ID, reference_id=REFERENCE_ID)
    handle_installment_due_soon(sender=None, user_id=USER_ID, reference_id=REFERENCE_ID)

    assert Notification.objects.count() == 1


def test_receiver_does_nothing_when_the_event_is_disabled():
    """Con la preferencia desactivada el receptor no crea el aviso."""
    from apps.notifications.receivers import handle_installment_due_soon
    from apps.notifications.services import set_preference

    set_preference(
        user_id=USER_ID,
        event_type=Notification.EventType.INSTALLMENT_DUE_SOON,
        enabled=False,
    )

    handle_installment_due_soon(sender=None, user_id=USER_ID, reference_id=REFERENCE_ID)

    assert Notification.objects.count() == 0


def test_receiver_dispatches_the_email_task():
    """El receptor encola la tarea de envío cuando la transacción se confirma."""
    from apps.notifications.receivers import handle_installment_overdue

    mail.outbox.clear()
    with override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True):
        handle_installment_overdue(
            sender=None,
            user_id=USER_ID,
            reference_id=REFERENCE_ID,
        )

    assert Notification.objects.filter(
        event_type=Notification.EventType.INSTALLMENT_OVERDUE,
    ).exists()
