"""Modelos de la app notifications: avisos al usuario y sus preferencias.

La app no guarda datos financieros: solo registra **qué** aviso se le manda a
**quién** y en qué estado quedó el envío.
"""

from django.db import models

from apps.core.models import BaseModel


class Notification(BaseModel):
    """Aviso de un evento, con el estado del envío.

    La unicidad de `(user_id, event_type, reference_id)` hace que el mismo
    evento no genere dos avisos: es la idempotencia de los receptores.
    """

    class EventType(models.TextChoices):
        """Tipos de evento que generan un aviso."""

        INSTALLMENT_DUE_SOON = 'installment_due_soon', 'Cuota por vencer'
        INSTALLMENT_OVERDUE = 'installment_overdue', 'Cuota vencida'
        INVESTMENT_SETTLED = 'investment_settled', 'Inversión liquidada'
        BUDGET_ALERT = 'budget_alert', 'Alerta de presupuesto'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        SENT = 'sent', 'Enviado'
        FAILED = 'failed', 'Fallido'

    user_id = models.UUIDField()
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    reference_id = models.UUIDField()
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    sent_at = models.DateTimeField(null=True, blank=True)
    error = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'event_type', 'reference_id'],
                name='notifications_notification_unique_per_event',
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'Notification<{self.user_id}:{self.event_type}:{self.status}>'


class NotificationPreference(BaseModel):
    """Preferencia del usuario sobre un tipo de evento.

    Si no hay fila, el evento está habilitado: el usuario solo crea la
    preferencia cuando quiere desactivarlo.
    """

    user_id = models.UUIDField()
    event_type = models.CharField(max_length=32, choices=Notification.EventType.choices)
    enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'event_type'],
                name='notifications_preference_unique_per_event',
            ),
        ]
        ordering = ['event_type']

    def __str__(self):
        return f'NotificationPreference<{self.user_id}:{self.event_type}:{self.enabled}>'
