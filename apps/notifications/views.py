"""Vistas de la API de notifications.

Las vistas son finas: validan la entrada, llaman a los selectores o services y
devuelven la respuesta. Cada usuario ve solo lo suyo.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination
from apps.notifications.exceptions import InvalidEventType
from apps.notifications.selectors import list_notifications_for_user
from apps.notifications.serializers import (
    NotificationPreferenceListSerializer,
    NotificationPreferenceSerializer,
    NotificationSerializer,
)
from apps.notifications.services import get_preferences, set_preference


class NotificationListView(APIView):
    """Avisos del usuario autenticado."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        responses={200: NotificationSerializer},
        summary='Listar los avisos propios',
        operation_id='notifications_list',
    )
    def get(self, request):
        """Lista los avisos del usuario, del más nuevo al más viejo."""
        notifications = list_notifications_for_user(user_id=request.user.id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(notifications, request, view=self)
        return paginator.get_paginated_response(NotificationSerializer(page, many=True).data)


class NotificationPreferenceView(APIView):
    """Preferencias de avisos del usuario autenticado."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: NotificationPreferenceListSerializer},
        summary='Ver las preferencias de avisos',
        operation_id='notifications_preferences',
    )
    def get(self, request):
        """Devuelve las preferencias del usuario con todos los eventos."""
        preferences = get_preferences(user_id=request.user.id)
        return Response(NotificationPreferenceListSerializer({'preferences': preferences}).data)

    @extend_schema(
        request=NotificationPreferenceSerializer,
        responses={200: NotificationPreferenceSerializer},
        summary='Activar o desactivar un tipo de aviso',
        operation_id='notifications_preferences_update',
    )
    def put(self, request):
        """Guarda si el usuario quiere recibir un tipo de aviso."""
        serializer = NotificationPreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            preference = set_preference(
                user_id=request.user.id,
                event_type=data['event_type'],
                enabled=data['enabled'],
            )
        except InvalidEventType as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc
        return Response(
            NotificationPreferenceSerializer(
                {'event_type': preference.event_type, 'enabled': preference.enabled}
            ).data,
            status=status.HTTP_200_OK,
        )
