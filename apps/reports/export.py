"""Exportación de los reportes a CSV.

Usa el módulo `csv` de la stdlib (sin dependencias) y neutraliza la inyección
de fórmulas: una celda que empieza por `=`, `+`, `-` o `@` se exporta con un
apóstrofo adelante, así la planilla no la interpreta como fórmula.
"""

import csv
import io
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal

from django.http import HttpResponse

from apps.reports.exceptions import ReportTooLarge

# Tope de filas por exportación CSV. Un reporte más largo se rechaza con 400
# en vez de bajar un archivo enorme.
MAX_EXPORT_ROWS = 10000

# Caracteres con los que una planilla interpreta una celda como fórmula.
FORMULA_PREFIXES = ('=', '+', '-', '@')


def format_cell(value: object) -> str:
    """Formatea un valor para el CSV y neutraliza la inyección de fórmulas.

    Args:
        value: valor de la fila.

    Returns:
        El texto de la celda.
    """
    if value is None:
        text = ''
    elif isinstance(value, datetime | date):
        text = value.isoformat()
    elif isinstance(value, Decimal):
        text = f'{value:.2f}'
    else:
        text = str(value)
    if text.startswith(FORMULA_PREFIXES):
        return f"'{text}"
    return text


def render_csv(rows: Sequence[dict], columns: Sequence[str], filename: str) -> HttpResponse:
    """Arma la respuesta CSV de un reporte.

    Args:
        rows: filas del reporte.
        columns: columnas, en orden.
        filename: nombre del archivo descargable.

    Returns:
        La respuesta HTTP con el CSV.

    Raises:
        ReportTooLarge: si el reporte supera el tope de filas exportables.
    """
    if len(rows) > MAX_EXPORT_ROWS:
        raise ReportTooLarge(f'El reporte supera el máximo de {MAX_EXPORT_ROWS} filas exportables.')
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator='\r\n')
    writer.writerow(list(columns))
    for row in rows:
        writer.writerow([format_cell(row.get(column, '')) for column in columns])
    response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
