"""Manejador de errores uniforme de la API (formato de AGENTS §8)."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

ERROR_CODES = {
    status.HTTP_400_BAD_REQUEST: 'validation_error',
    status.HTTP_401_UNAUTHORIZED: 'not_authenticated',
    status.HTTP_403_FORBIDDEN: 'permission_denied',
    status.HTTP_404_NOT_FOUND: 'not_found',
    status.HTTP_405_METHOD_NOT_ALLOWED: 'method_not_allowed',
    status.HTTP_409_CONFLICT: 'conflict',
    status.HTTP_429_TOO_MANY_REQUESTS: 'throttled',
}

# Para estos status se conserva el código genérico del status HTTP.
# En los demás (por ejemplo 409) manda el código propio de la excepción.
GENERIC_CODE_STATUSES = frozenset(
    {
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_405_METHOD_NOT_ALLOWED,
        status.HTTP_429_TOO_MANY_REQUESTS,
    }
)

DEFAULT_MESSAGES = {
    status.HTTP_400_BAD_REQUEST: 'Los datos enviados no son válidos.',
    status.HTTP_401_UNAUTHORIZED: 'Debés autenticarte para acceder a este recurso.',
    status.HTTP_403_FORBIDDEN: 'No tenés permisos para realizar esta acción.',
    status.HTTP_404_NOT_FOUND: 'El recurso solicitado no existe.',
    status.HTTP_405_METHOD_NOT_ALLOWED: 'El método HTTP no está permitido para este recurso.',
    status.HTTP_409_CONFLICT: 'La solicitud entra en conflicto con el estado actual.',
    status.HTTP_429_TOO_MANY_REQUESTS: 'Demasiadas solicitudes. Intentá de nuevo más tarde.',
}


def api_exception_handler(exc, context) -> Response | None:
    """Normaliza los errores de DRF al formato de AGENTS §8.

    Args:
        exc: excepción lanzada durante la resolución de la vista.
        context: contexto de la vista (request, view, etc.).

    Returns:
        Response con el cuerpo {"error": {"code", "message", "details"}},
        o None si la excepción no proviene de la API.
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    code = ERROR_CODES.get(response.status_code, 'api_error')
    message = DEFAULT_MESSAGES.get(response.status_code, 'Ocurrió un error en la solicitud.')
    details = response.data

    if isinstance(details, dict) and 'detail' in details:
        detail = details['detail']
        message = str(detail)
        details = {}
        detail_code = getattr(detail, 'code', None)
        if detail_code and response.status_code not in GENERIC_CODE_STATUSES:
            code = detail_code

    response.data = {'error': {'code': code, 'message': message, 'details': details}}
    return response
