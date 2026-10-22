"""Servicios de escritura de la app notifications (interfaz pública)."""

import uuid
from datetime import UTC, datetime

from django.utils import timezone

from apps.notifications.exceptions import InvalidEventType
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.selectors import (
    get_notification_for_user,
    get_preference_for_user,
    list_preferences_for_user,
)


def create_notification(
    user_id: uuid.UUID,
    event_type: str,
    reference_id: uuid.UUID,
) -> Notification | None:
    """Crea el aviso de un evento, si el usuario lo tiene habilitado.

    Es **idempotente**: el mismo `(usuario, evento, referencia)` devuelve siempre
    el mismo aviso, así que un receptor que corre dos veces no duplica nada.

    Args:
        user_id: identificador del destinatario.
        event_type: tipo de evento.
        reference_id: identificador de lo que originó el evento (la cuota, la
            posición o el presupuesto del mes).

    Returns:
        El Notification creado o el existente; None si el usuario desactivó el
        evento.

    Raises:
        InvalidEventType: si el tipo de evento no es del proyecto.
    """
    if event_type not in Notification.EventType.values:
        raise InvalidEventType(f'El evento {event_type} no es un evento del proyecto.')
    preference = get_preference_for_user(user_id=user_id, event_type=event_type)
    if preference is not None and not preference.enabled:
        return None
    notification, _ = Notification.objects.get_or_create(
        user_id=user_id,
        event_type=event_type,
        reference_id=reference_id,
        defaults={'status': Notification.Status.PENDING},
    )
    return notification


def set_preference(user_id: uuid.UUID, event_type: str, enabled: bool) -> NotificationPreference:
    """Guarda si el usuario quiere recibir un tipo de evento.

    Args:
        user_id: identificador del usuario.
        event_type: tipo de evento.
        enabled: True para recibirlo, False para desactivarlo.

    Returns:
        La NotificationPreference guardada.

    Raises:
        InvalidEventType: si el tipo de evento no es del proyecto.
    """
    if event_type not in Notification.EventType.values:
        raise InvalidEventType(f'El evento {event_type} no es un evento del proyecto.')
    preference, _ = NotificationPreference.objects.update_or_create(
        user_id=user_id,
        event_type=event_type,
        defaults={'enabled': enabled},
    )
    return preference


def mark_notification_read(
    user_id: uuid.UUID,
    notification_id: uuid.UUID,
) -> Notification | None:
    """Marca un aviso del usuario como le\u00eddo.

    Es idempotente: si ya estaba le\u00eddo, no cambia el `read_at`.

    Args:
        user_id: identificador del usuario dueno del aviso.
        notification_id: identificador del aviso.

    Returns:
        El Notification leído, o None si no existe o es de otro usuario.
    """
    notification = get_notification_for_user(user_id=user_id, notification_id=notification_id)
    if notification is None:
        return None
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=['read_at'])
    return notification


def mark_all_notifications_read(user_id: uuid.UUID) -> int:
    """Marca como le\u00eddos todos los avisos que el usuario todav\u00eda no ley\u00f3.

    Es idempotente: la segunda vez no marca ninguno.

    Args:
        user_id: identificador del usuario.

    Returns:
        La cantidad de avisos marcados en esta llamada.
    """
    return Notification.objects.filter(user_id=user_id, read_at__isnull=True).update(
        read_at=timezone.now()
    )


def get_preferences(user_id: uuid.UUID) -> list[dict]:
    """Devuelve las preferencias del usuario con todos los eventos.

    Los eventos sin fila guardada están habilitados: es el valor por defecto.

    Args:
        user_id: identificador del usuario.

    Returns:
        Lista de preferencias con el tipo de evento y si está habilitado.
    """
    stored = {
        preference.event_type: preference.enabled
        for preference in list_preferences_for_user(user_id=user_id)
    }
    return [
        {'event_type': event_type, 'enabled': stored.get(event_type, True)}
        for event_type in Notification.EventType.values
    ]


def mark_notification_sent(notification: Notification) -> Notification:
    """Marca un aviso como enviado.

    Args:
        notification: el aviso.

    Returns:
        El aviso actualizado.
    """
    notification.status = Notification.Status.SENT
    notification.sent_at = datetime.now(UTC)
    notification.error = ''
    notification.save(update_fields=['status', 'sent_at', 'error', 'updated_at'])
    return notification


def mark_notification_failed(notification: Notification, error: str) -> Notification:
    """Marca un aviso como fallido, guardando el motivo.

    Args:
        notification: el aviso.
        error: motivo del fallo, sin datos sensibles.

    Returns:
        El aviso actualizado.
    """
    notification.status = Notification.Status.FAILED
    notification.error = error[:255]
    notification.save(update_fields=['status', 'error', 'updated_at'])
    return notification
