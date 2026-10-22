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
            'read_at',
            'error',
        ]
        read_only_fields = fields


class UnreadCountSerializer(serializers.Serializer):
    """La cantidad de avisos sin leer."""

    count = serializers.IntegerField(
        help_text='Avisos que el usuario todav\u00eda no ley\u00f3.',
    )


class ReadAllSerializer(serializers.Serializer):
    """Cuantos avisos se marcaron como leídos."""

    count = serializers.IntegerField(
        help_text='Avisos marcados como le\u00eddos en esta llamada.',
    )


class NotificationPreferenceSerializer(serializers.Serializer):
    """La preferencia de un tipo de evento."""

    event_type = serializers.ChoiceField(choices=Notification.EventType.choices)
    enabled = serializers.BooleanField()


class NotificationPreferenceListSerializer(serializers.Serializer):
    """Las preferencias del usuario con todos los eventos."""

    preferences = NotificationPreferenceSerializer(many=True)
