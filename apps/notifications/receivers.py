"""Receptores de las señales de las apps emisoras (AGENTS §5.3).

Cada receptor hace una sola cosa: crear el aviso con
`notifications.services` y delegar el envío a la tarea de Celery. No hay lógica
de negocio acá y el envío nunca ocurre dentro de la transacción que originó el
evento: se encola con `transaction.on_commit`.
"""

from django.db import transaction
from django.dispatch import receiver

from apps.budgets.signals import budget_alert
from apps.investments.signals import investment_settled
from apps.loans.signals import installment_due_soon, installment_overdue
from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from apps.notifications.tasks import send_notification_email


def dispatch_notification(user_id, event_type: str, reference_id) -> None:
    """Crea el aviso de un evento y encola el envío del email.

    Args:
        user_id: identificador del destinatario.
        event_type: tipo de evento.
        reference_id: identificador de lo que originó el evento.
    """
    notification = create_notification(
        user_id=user_id,
        event_type=event_type,
        reference_id=reference_id,
    )
    if notification is None:
        return
    transaction.on_commit(lambda: send_notification_email.delay(str(notification.id)))


@receiver(installment_due_soon)
def handle_installment_due_soon(sender, user_id, reference_id, **kwargs):
    """Avisa al prestatario de una cuota que está por vencer."""
    dispatch_notification(
        user_id=user_id,
        event_type=Notification.EventType.INSTALLMENT_DUE_SOON,
        reference_id=reference_id,
    )


@receiver(installment_overdue)
def handle_installment_overdue(sender, user_id, reference_id, **kwargs):
    """Avisa al prestatario y al prestamista de una cuota vencida."""
    dispatch_notification(
        user_id=user_id,
        event_type=Notification.EventType.INSTALLMENT_OVERDUE,
        reference_id=reference_id,
    )


@receiver(investment_settled)
def handle_investment_settled(sender, user_id, reference_id, **kwargs):
    """Avisa al inversionista de que su posición se liquidó."""
    dispatch_notification(
        user_id=user_id,
        event_type=Notification.EventType.INVESTMENT_SETTLED,
        reference_id=reference_id,
    )


@receiver(budget_alert)
def handle_budget_alert(sender, user_id, reference_id, **kwargs):
    """Avisa al usuario de que su presupuesto cruzó el umbral."""
    dispatch_notification(
        user_id=user_id,
        event_type=Notification.EventType.BUDGET_ALERT,
        reference_id=reference_id,
    )
