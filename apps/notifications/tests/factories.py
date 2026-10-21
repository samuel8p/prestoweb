"""Factories de la app notifications."""

import uuid

import factory

from apps.notifications.models import Notification


class NotificationFactory(factory.django.DjangoModelFactory):
    """Factory de Notification."""

    class Meta:
        model = Notification

    user_id = factory.LazyFunction(uuid.uuid4)
    event_type = Notification.EventType.INSTALLMENT_DUE_SOON
    reference_id = factory.LazyFunction(uuid.uuid4)
    status = Notification.Status.PENDING
