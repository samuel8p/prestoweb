"""Serializers de la app notifications: solo validan entrada y dan formato a la salida."""

from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Un aviso del usuario."""

    class Meta:
        model = Notification
        fields = [
            'id',
            'user_id',
            'event_type',
            'reference_id',
            'status',
            'created_at',
            'sent_at',
            'error',
        ]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.Serializer):
    """La preferencia de un tipo de evento."""

    event_type = serializers.ChoiceField(choices=Notification.EventType.choices)
    enabled = serializers.BooleanField()


class NotificationPreferenceListSerializer(serializers.Serializer):
    """Las preferencias del usuario con todos los eventos."""

    preferences = NotificationPreferenceSerializer(many=True)
