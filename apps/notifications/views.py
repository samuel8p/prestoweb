"""Vistas de la API de notifications.

Las vistas son finas: validan la entrada, llaman a los selectores o services y
devuelven la respuesta. Cada usuario ve solo lo suyo.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.openapi import paginated_response
from apps.core.pagination import StandardPagination
from apps.notifications.selectors import (
    count_unread_for_user,
    list_notifications_for_user,
)
from apps.notifications.serializers import (
    NotificationPreferenceListSerializer,
    NotificationPreferenceSerializer,
    NotificationSerializer,
    ReadAllSerializer,
    UnreadCountSerializer,
)
from apps.notifications.services import (
    get_preferences,
    mark_all_notifications_read,
    mark_notification_read,
    set_preference,
)


class NotificationListView(APIView):
    """Avisos del usuario autenticado."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        responses={200: paginated_response(NotificationSerializer)},
        summary='Listar los avisos propios',
        operation_id='notifications_list',
    )
    def get(self, request):
        """Lista los avisos del usuario, del más nuevo al más viejo."""
        notifications = list_notifications_for_user(user_id=request.user.id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(notifications, request, view=self)
        return paginator.get_paginated_response(NotificationSerializer(page, many=True).data)


class NotificationReadView(APIView):
    """Marca un aviso propio como le\u00eddo."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: NotificationSerializer},
        summary='Marcar un aviso como le\u00eddo',
        operation_id='notifications_read',
    )
    def post(self, request, notification_id):
        """Marca el aviso como le\u00eddo (idempotente)."""
        notification = mark_notification_read(
            user_id=request.user.id,
            notification_id=notification_id,
        )
        if notification is None:
            raise NotFound('El aviso no existe.')
        return Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)


class NotificationReadAllView(APIView):
    """Marca todos los avisos propios como le\u00eddos."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: ReadAllSerializer},
        summary='Marcar todos los avisos como le\u00eddos',
        operation_id='notifications_read_all',
    )
    def post(self, request):
        """Marca todos los avisos sin leer (idempotente)."""
        count = mark_all_notifications_read(user_id=request.user.id)
        return Response({'count': count}, status=status.HTTP_200_OK)


class NotificationUnreadCountView(APIView):
    """Cantidad de avisos que el usuario todav\u00eda no ley\u00f3."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: UnreadCountSerializer},
        summary='Ver la cantidad de avisos sin leer',
        operation_id='notifications_unread_count',
    )
    def get(self, request):
        """Devuelve la cantidad de avisos sin leer."""
        return Response(
            {'count': count_unread_for_user(user_id=request.user.id)},
            status=status.HTTP_200_OK,
        )


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
        preference = set_preference(
            user_id=request.user.id,
            event_type=data['event_type'],
            enabled=data['enabled'],
        )
        return Response(
            NotificationPreferenceSerializer(
                {'event_type': preference.event_type, 'enabled': preference.enabled}
            ).data,
            status=status.HTTP_200_OK,
        )
