"""Selectores de lectura de la app notifications (interfaz pública)."""

import uuid

from django.db.models import QuerySet

from apps.notifications.models import Notification, NotificationPreference


def list_notifications_for_user(user_id: uuid.UUID) -> QuerySet[Notification]:
    """Lista los avisos del usuario.

    Args:
        user_id: identificador del usuario.

    Returns:
        QuerySet con los avisos del usuario, del más nuevo al más viejo.
    """
    return Notification.objects.filter(user_id=user_id).order_by('-created_at')


def get_notification_for_user(
    user_id: uuid.UUID, notification_id: uuid.UUID
) -> Notification | None:
    """Devuelve un aviso del usuario, o None si no existe o es de otro.

    Args:
        user_id: identificador del usuario propietario.
        notification_id: identificador del aviso.

    Returns:
        El Notification del usuario o None.
    """
    return Notification.objects.filter(id=notification_id, user_id=user_id).first()


def get_notification(notification_id: uuid.UUID) -> Notification | None:
    """Devuelve un aviso por su id, sin filtrar por usuario.

    Lo usa la tarea de envío, que ya tiene el aviso y su destinatario.

    Args:
        notification_id: identificador del aviso.

    Returns:
        El Notification o None.
    """
    return Notification.objects.filter(id=notification_id).first()


def get_preference_for_user(
    user_id: uuid.UUID,
    event_type: str,
) -> NotificationPreference | None:
    """Devuelve la preferencia guardada del usuario para un evento, o None.

    Args:
        user_id: identificador del usuario.
        event_type: tipo de evento.

    Returns:
        La NotificationPreference o None (si no hay fila, está habilitado).
    """
    return NotificationPreference.objects.filter(user_id=user_id, event_type=event_type).first()


def list_preferences_for_user(user_id: uuid.UUID) -> QuerySet[NotificationPreference]:
    """Lista las preferencias guardadas del usuario.

    Args:
        user_id: identificador del usuario.

    Returns:
        QuerySet con las preferencias del usuario.
    """
    return NotificationPreference.objects.filter(user_id=user_id).order_by('event_type')
