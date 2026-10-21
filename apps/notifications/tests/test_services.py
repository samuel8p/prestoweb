"""Tests de los servicios de la app notifications."""

import uuid

import pytest

from apps.notifications.tests.factories import NotificationFactory

pytestmark = pytest.mark.django_db

USER_ID = uuid.UUID('11111111-1111-1111-1111-111111111111')
OTHER_USER_ID = uuid.UUID('33333333-3333-3333-3333-333333333333')
REFERENCE_ID = uuid.UUID('22222222-2222-2222-2222-222222222222')


def test_create_notification_creates_a_pending_notification():
    """El servicio crea el aviso en estado pendiente."""
    from apps.notifications.models import Notification
    from apps.notifications.services import create_notification

    notification = create_notification(
        user_id=USER_ID,
        event_type=Notification.EventType.INSTALLMENT_DUE_SOON,
        reference_id=REFERENCE_ID,
    )

    assert notification is not None
    assert notification.status == Notification.Status.PENDING
    assert notification.sent_at is None
    assert notification.error == ''


def test_create_notification_is_idempotent():
    """El mismo evento dos veces deja un solo aviso."""
    from apps.notifications.models import Notification
    from apps.notifications.services import create_notification

    first = create_notification(
        user_id=USER_ID,
        event_type=Notification.EventType.INSTALLMENT_DUE_SOON,
        reference_id=REFERENCE_ID,
    )
    second = create_notification(
        user_id=USER_ID,
        event_type=Notification.EventType.INSTALLMENT_DUE_SOON,
        reference_id=REFERENCE_ID,
    )

    assert first.id == second.id
    assert (
        Notification.objects.filter(
            user_id=USER_ID,
            event_type=Notification.EventType.INSTALLMENT_DUE_SOON,
            reference_id=REFERENCE_ID,
        ).count()
        == 1
    )


def test_create_notification_does_not_repeat_for_another_event_type():
    """El mismo aviso con otro tipo de evento es otro aviso."""
    from apps.notifications.models import Notification
    from apps.notifications.services import create_notification

    first = create_notification(
        user_id=USER_ID,
        event_type=Notification.EventType.INSTALLMENT_DUE_SOON,
        reference_id=REFERENCE_ID,
    )
    second = create_notification(
        user_id=USER_ID,
        event_type=Notification.EventType.INSTALLMENT_OVERDUE,
        reference_id=REFERENCE_ID,
    )

    assert first.id != second.id


def test_create_notification_respects_a_disabled_preference():
    """Con la preferencia desactivada no se crea el aviso."""
    from apps.notifications.models import Notification
    from apps.notifications.services import create_notification, set_preference

    set_preference(
        user_id=USER_ID,
        event_type=Notification.EventType.INSTALLMENT_DUE_SOON,
        enabled=False,
    )

    notification = create_notification(
        user_id=USER_ID,
        event_type=Notification.EventType.INSTALLMENT_DUE_SOON,
        reference_id=REFERENCE_ID,
    )

    assert notification is None
    assert Notification.objects.count() == 0


def test_set_preference_disables_and_enables_an_event():
    """La preferencia se puede desactivar y volver a activar."""
    from apps.notifications.models import Notification
    from apps.notifications.services import get_preferences, set_preference

    disabled = set_preference(
        user_id=USER_ID,
        event_type=Notification.EventType.INSTALLMENT_OVERDUE,
        enabled=False,
    )
    assert disabled.enabled is False

    enabled = set_preference(
        user_id=USER_ID,
        event_type=Notification.EventType.INSTALLMENT_OVERDUE,
        enabled=True,
    )
    assert enabled.enabled is True

    preferences = {
        preference['event_type']: preference['enabled'] for preference in get_preferences(USER_ID)
    }
    assert preferences[Notification.EventType.INSTALLMENT_OVERDUE] is True


def test_get_preferences_returns_every_event_enabled_by_default():
    """Sin preferencias guardadas, todos los eventos están habilitados."""
    from apps.notifications.models import Notification
    from apps.notifications.services import get_preferences

    preferences = {
        preference['event_type']: preference['enabled'] for preference in get_preferences(USER_ID)
    }

    assert set(preferences) == set(Notification.EventType.values)
    assert all(preferences.values())


def test_get_preferences_isolates_users():
    """Cada usuario ve solo sus preferencias."""
    from apps.notifications.models import Notification
    from apps.notifications.services import get_preferences, set_preference

    set_preference(
        user_id=USER_ID,
        event_type=Notification.EventType.BUDGET_ALERT,
        enabled=False,
    )

    preferences = {
        preference['event_type']: preference['enabled']
        for preference in get_preferences(OTHER_USER_ID)
    }

    assert preferences[Notification.EventType.BUDGET_ALERT] is True


def test_list_notifications_for_user_isolates_users():
    """Cada usuario ve solo sus avisos."""
    from apps.notifications.selectors import list_notifications_for_user

    NotificationFactory(user_id=USER_ID, event_type='installment_due_soon')
    NotificationFactory(user_id=OTHER_USER_ID, event_type='installment_due_soon')

    notifications = list_notifications_for_user(USER_ID)

    assert len(notifications) == 1
    assert notifications[0].user_id == USER_ID


def test_get_notification_for_user_returns_none_for_another_user():
    """Un aviso ajeno no se expone."""
    from apps.notifications.selectors import get_notification_for_user

    notification = NotificationFactory(user_id=USER_ID)

    assert get_notification_for_user(USER_ID, notification.id) is not None
    assert get_notification_for_user(OTHER_USER_ID, notification.id) is None
