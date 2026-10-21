"""Vistas transversales de la app core.

El chequeo de salud es un endpoint **operativo**: vive fuera de `/api/v1/`, no
pide autenticación y no aplica throttling. Solo dice si el servicio puede
hablar con la base de datos; no expone detalles internos ni secretos.

El endpoint de metadata es **público** y dice en qué modo corre la aplicación
(`demo` o `production`) y si el dinero es simulado.
"""

import logging

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.serializers import MetaSerializer

logger = logging.getLogger(__name__)


def health_check(request):
    """Responde 200 si la base de datos contesta y 503 si no.

    Args:
        request: la petición HTTP (no se usa: el chequeo no tiene parámetros).

    Returns:
        JsonResponse con `{"status": "ok"}` o `{"status": "unavailable"}`.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        logger.exception('El chequeo de salud no pudo consultar la base de datos.')
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ok'}, status=200)


class MetaView(APIView):
    """Metadata pública de la aplicación: modo y dinero simulado."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    @extend_schema(
        responses={200: MetaSerializer},
        summary='Ver el modo de la aplicación',
        operation_id='meta',
    )
    def get(self, request):
        """Devuelve el modo de la aplicación y si el dinero es simulado."""
        return Response(
            {
                'mode': 'demo' if settings.DEMO_MODE else 'production',
                'simulated_money': settings.LEDGER_SIMULATED_DEPOSITS_ENABLED,
            }
        )
