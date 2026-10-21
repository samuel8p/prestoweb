"""Tareas Celery de la app notifications.

El envío es una tarea: un fallo de SMTP no rompe la transacción de la app
que originó el evento ni el ledger.
"""

import logging
import uuid

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from apps.identity.selectors import get_user_email
from apps.notifications.emails import build_email
from apps.notifications.models import Notification
from apps.notifications.selectors import get_notification
from apps.notifications.services import mark_notification_failed, mark_notification_sent

logger = logging.getLogger(__name__)


@shared_task(name='apps.notifications.tasks.send_notification_email')
def send_notification_email(notification_id: str) -> bool:
    """Envía el email de un aviso pendiente.

    Es **idempotente**: un aviso que ya está enviado no se vuelve a mandar.

    Args:
        notification_id: identificador del aviso.

    Returns:
        True si el email se envió, False si no había nada que enviar.
    """
    notification = get_notification(uuid.UUID(str(notification_id)))
    if notification is None:
        return False
    if notification.status != Notification.Status.PENDING:
        return False
    recipient = get_user_email(user_id=notification.user_id)
    if not recipient:
        mark_notification_failed(notification, 'El usuario no tiene un email registrado.')
        return False
    subject, body = build_email(notification)
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception('No se pudo enviar el aviso %s', notification.id)
        mark_notification_failed(notification, str(exc))
        return False
    logger.info(
        'Aviso enviado: notification_id=%s event_type=%s', notification.id, notification.event_type
    )
    mark_notification_sent(notification)
    return True
