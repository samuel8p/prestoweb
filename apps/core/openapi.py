"""Piezas del esquema OpenAPI compartidas por las vistas.

El esquema tiene que describir **exactamente** lo que la API hace: la
paginación real (dos paginaciones distintas), el header `Idempotency-Key`, los
parámetros de los reportes y el formato de error de AGENTS §8.

Nada de esto cambia el comportamiento de la API: son declaraciones de
documentación (serializers y `extend_schema`).
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse
from rest_framework import serializers

from apps.core.exception_handler import DEFAULT_MESSAGES

# --- Formato de error (AGENTS §8) ---

ERROR_CODES_BY_STATUS = {
    400: 'validation_error',
    401: 'not_authenticated',
    403: 'permission_denied',
    404: 'not_found',
    405: 'method_not_allowed',
    409: 'conflict',
    429: 'throttled',
}

ERROR_DESCRIPTIONS = {
    400: 'Los datos enviados no son válidos (el `details` dice el campo).',
    401: 'Falta el token o venció.',
    403: 'Sin permiso, o con el KYC sin aprobar.',
    404: 'El recurso no existe o no es del usuario.',
    405: 'El método HTTP no está permitido para este recurso.',
    409: 'Conflicto con el estado actual (por ejemplo, la misma clave de '
    'idempotencia con otro payload).',
    429: 'Demasiados intentos (throttle).',
}


class ErrorDetailSerializer(serializers.Serializer):
    """Cuerpo del error de la API."""

    code = serializers.CharField(
        help_text='Código del error (por ejemplo, `validation_error`).',
    )
    message = serializers.CharField(help_text='Mensaje legible en español.')
    details = serializers.JSONField(
        required=False,
        allow_null=True,
        help_text='Errores por campo: el nombre del campo y la lista de mensajes.',
    )


class ErrorResponseSerializer(serializers.Serializer):
    """Respuesta de error de la API (el formato de AGENTS §8)."""

    error = ErrorDetailSerializer()


# --- Paginación ---


def _pagination_serializer(serializer_class, cursor: bool):
    """Crea el serializer de la respuesta paginada de un listado.

    Args:
        serializer_class: el serializer de los elementos del listado.
        cursor: si la paginación es por cursor (sin `count`).

    Returns:
        La clase de serializer de la respuesta paginada.
    """
    fields = {
        'next': serializers.URLField(
            allow_null=True,
            help_text='URL de la página siguiente (null si es la última).',
        ),
        'previous': serializers.URLField(
            allow_null=True,
            help_text='URL de la página anterior (null si es la primera).',
        ),
        'results': serializer_class(many=True),
    }
    if not cursor:
        fields['count'] = serializers.IntegerField(
            help_text='Cantidad total de elementos del listado.',
        )

    name = f"{'Cursor' if cursor else ''}Paginated{serializer_class.__name__}"
    return type(name, (serializers.Serializer,), fields)


def paginated_response(serializer_class, description: str = 'Listado paginado.'):
    """Declara la respuesta de un listado paginado por página.

    La API devuelve `{"count", "next", "previous", "results"}` ✓.
    """
    return OpenApiResponse(
        response=_pagination_serializer(serializer_class, cursor=False),
        description=description,
    )


def cursor_paginated_response(serializer_class, description: str = 'Listado paginado por cursor.'):
    """Declara la respuesta de un listado paginado por cursor.

    La API devuelve `{"next", "previous", "results"}` (sin `count` ✓).
    """
    return OpenApiResponse(
        response=_pagination_serializer(serializer_class, cursor=True),
        description=description,
    )


# --- Header de idempotencia ---

IDEMPOTENCY_KEY_PARAMETER = OpenApiParameter(
    name='Idempotency-Key',
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=True,
    description=(
        'Clave de idempotencia, única por usuario. Con la misma clave y el mismo '
        'payload la API devuelve la operación original; con la misma clave y otro '
        'payload responde 409 (`idempotency_conflict`).'
    ),
)


# --- Errores ---


def error_responses(*statuses: int) -> dict[int, OpenApiResponse]:
    """Declara las respuestas de error con el formato de AGENTS §8.

    Args:
        statuses: los códigos HTTP que puede devolver la operación.

    Returns:
        El diccionario para el `responses` de `extend_schema`.
    """
    responses = {}
    for status_code in statuses:
        code = ERROR_CODES_BY_STATUS.get(status_code, 'api_error')
        message = DEFAULT_MESSAGES.get(status_code, 'Ocurrió un error en la solicitud.')
        responses[status_code] = OpenApiResponse(
            response=ErrorResponseSerializer,
            description=ERROR_DESCRIPTIONS.get(status_code, 'Error.'),
            example={'error': {'code': code, 'message': message, 'details': {}}},
        )
    return responses


# --- Parámetros de los reportes ---

CURRENCY_PARAMETER = OpenApiParameter(
    name='currency',
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    required=True,
    description='Moneda del reporte: `ARS` o `USD`. Sin ella la API responde 400.',
    enum=['ARS', 'USD'],
)

FROM_PARAMETER = OpenApiParameter(
    name='from',
    type=OpenApiTypes.DATE,
    location=OpenApiParameter.QUERY,
    required=False,
    description=(
        'Fecha inicial del rango (ISO, `YYYY-MM-DD`). Por defecto, el primer día '
        'del mes actual en UTC.'
    ),
)

TO_PARAMETER = OpenApiParameter(
    name='to',
    type=OpenApiTypes.DATE,
    location=OpenApiParameter.QUERY,
    required=False,
    description=(
        'Fecha final del rango (ISO, `YYYY-MM-DD`). Por defecto, el último día del '
        'mes actual en UTC.'
    ),
)

EXPORT_PARAMETER = OpenApiParameter(
    name='export',
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    required=False,
    description=(
        'Con `csv` la API responde el CSV (con `Content-Disposition: attachment`). '
        'Cualquier otro valor responde 400.'
    ),
    enum=['csv'],
)

REPORT_PARAMETERS = [CURRENCY_PARAMETER, FROM_PARAMETER, TO_PARAMETER, EXPORT_PARAMETER]

CSV_RESPONSE = OpenApiResponse(
    response={
        'type': 'string',
        'format': 'binary',
    },
    description='El reporte en CSV (con `Content-Disposition: attachment`).',
)


def report_responses(serializer_class, description: str = 'El reporte en JSON.'):
    """Las respuestas de un reporte: el JSON (y el CSV, con el hook).

    Args:
        serializer_class: el serializer del reporte, o la respuesta ya armada
            (el reporte de movimientos pagina).
        description: la descripción de la respuesta JSON.

    Returns:
        El diccionario para el `responses` de `extend_schema`.
    """
    if isinstance(serializer_class, OpenApiResponse):
        return {200: serializer_class}
    return {200: OpenApiResponse(response=serializer_class, description=description)}
