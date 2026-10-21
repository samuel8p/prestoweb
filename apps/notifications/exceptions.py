"""Excepciones de dominio de la app notifications."""

from apps.core.exceptions import DomainError


class NotificationsError(DomainError):
    """Error de dominio de notifications."""


class InvalidEventType(NotificationsError):
    """El tipo de evento no es uno de los del proyecto."""


class NotificationNotFound(NotificationsError):
    """El aviso no existe o no es del usuario."""
