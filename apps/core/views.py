"""Vistas transversales de la app core.

El chequeo de salud es un endpoint **operativo**: vive fuera de `/api/v1/`, no
pide autenticación y no aplica throttling. Solo dice si el servicio puede
hablar con la base de datos; no expone detalles internos ni secretos.
"""

import logging

from django.db import connection
from django.http import JsonResponse

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
