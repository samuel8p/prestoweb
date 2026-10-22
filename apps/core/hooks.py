"""Hooks de drf-spectacular (solo documentación del esquema)."""

from apps.core.openapi import (
    DEFAULT_MESSAGES,
    ERROR_CODES_BY_STATUS,
    ERROR_DESCRIPTIONS,
    ERROR_RESPONSE_SCHEMA,
    ERRORS_BY_OPERATION,
)

REPORT_PATHS = {
    '/api/v1/reports/spending/',
    '/api/v1/reports/loans/',
    '/api/v1/reports/investments/',
    '/api/v1/reports/movements/',
}

CSV_SCHEMA = {'type': 'string', 'format': 'binary'}

# Las respuestas que pueden venir `null` (el componente al que se le suma
# el "null" del JSON Schema).
NULLABLE_RESPONSES = {
    ('/api/v1/kyc/', 'get'): '#/components/schemas/KYCVerification',
}


def add_csv_response_to_the_reports(result, generator, request, public):
    """Le declara la respuesta CSV a los cuatro reportes.

    La API responde el CSV cuando llega `?export=csv` (con
    `Content-Disposition: attachment`), así que el esquema tiene que decirlo:
    el frontend baja el reporte con la misma ruta.
    """
    for path, operations in result.get('paths', {}).items():
        if path not in REPORT_PATHS:
            continue
        for operation in operations.values():
            content = operation['responses']['200']['content']
            content['text/csv'] = {'schema': dict(CSV_SCHEMA)}
    return result


def add_nullable_responses(result, generator, request, public):
    """Declara que hay respuestas que pueden venir `null`.

    `GET /api/v1/kyc/` devuelve `null` cuando el usuario todavía no pidió la
    verificación: el esquema lo decía como un objeto y el frontend tenía que
    adivinar.
    """
    for path, operations in result.get('paths', {}).items():
        for method, operation in operations.items():
            reference = NULLABLE_RESPONSES.get((path, method))
            if reference is None:
                continue
            content = operation['responses']['200']['content']
            content['application/json']['schema'] = {
                # OpenAPI 3.0: la forma nullable es "nullable: true".
                'allOf': [{'$ref': reference}],
                'nullable': True,
            }
    return result


def add_error_responses(result, generator, request, public):
    """Le declara a cada operación los errores que puede devolver.

    El formato es el de AGENTS §8: `{"error": {"code", "message", "details"}}`.
    El 403 es el del KYC sin aprobar.
    """
    for path, operations in result.get('paths', {}).items():
        for method, operation in operations.items():
            statuses = ERRORS_BY_OPERATION.get((path, method))
            if not statuses:
                continue
            responses = operation['responses']
            for status_code in statuses:
                code = ERROR_CODES_BY_STATUS.get(status_code, 'api_error')
                message = DEFAULT_MESSAGES.get(status_code, 'Ocurrió un error en la solicitud.')
                responses[str(status_code)] = {
                    'description': ERROR_DESCRIPTIONS.get(status_code, 'Error.'),
                    'content': {
                        'application/json': {
                            'schema': ERROR_RESPONSE_SCHEMA,
                            'example': {
                                'error': {
                                    'code': code,
                                    'message': message,
                                    'details': {},
                                },
                            },
                        },
                    },
                }
    return result
