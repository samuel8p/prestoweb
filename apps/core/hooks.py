"""Hooks de drf-spectacular (solo documentación del esquema)."""

REPORT_PATHS = {
    '/api/v1/reports/spending/',
    '/api/v1/reports/loans/',
    '/api/v1/reports/investments/',
    '/api/v1/reports/movements/',
}

CSV_SCHEMA = {'type': 'string', 'format': 'binary'}


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
