"""Selectores de lectura de la app reports (interfaz pública).

La app es **solo lectura**: no tiene modelos ni escrituras. Acá viven la
validación de los parámetros de cada reporte y las agregaciones.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from apps.reports.exceptions import InvalidReportParameters

# Monedas del proyecto (AGENTS §6: un reporte es de una sola moneda, nunca se
# mezclan ni se convierten).
CURRENCIES = ('ARS', 'USD')

# Rango máximo de un reporte, en meses calendario.
MAX_RANGE_MONTHS = 12


@dataclass(frozen=True)
class ReportPeriod:
    """Rango de fechas de un reporte, en UTC."""

    start_date: date
    end_date: date

    @property
    def start_datetime(self) -> datetime:
        """Inicio del rango como datetime UTC."""
        return datetime(
            self.start_date.year, self.start_date.month, self.start_date.day, tzinfo=UTC
        )

    @property
    def end_datetime(self) -> datetime:
        """Fin del rango como datetime UTC, inclusivo."""
        return datetime(
            self.end_date.year,
            self.end_date.month,
            self.end_date.day,
            23,
            59,
            59,
            999999,
            tzinfo=UTC,
        )


def parse_currency(params: Mapping[str, str]) -> str:
    """Valida la moneda del reporte.

    Args:
        params: parámetros de la query string.

    Returns:
        La moneda del reporte (`ARS` o `USD`).

    Raises:
        InvalidReportParameters: si falta o no es una moneda del proyecto.
    """
    raw = params.get('currency')
    if not raw:
        raise InvalidReportParameters('El parámetro currency es obligatorio (ARS o USD).')
    if raw not in CURRENCIES:
        raise InvalidReportParameters(f'La moneda {raw} no es válida (usá ARS o USD).')
    return raw


def parse_period(params: Mapping[str, str], today: date | None = None) -> ReportPeriod:
    """Valida el rango de fechas del reporte.

    Por defecto el reporte cubre el mes calendario actual en UTC. El rango no
    puede cubrir más de 12 meses calendario.

    Args:
        params: parámetros de la query string.
        today: fecha de referencia para el valor por defecto.

    Returns:
        El rango del reporte.

    Raises:
        InvalidReportParameters: si las fechas no son válidas o el rango es
            mayor a 12 meses calendario.
    """
    reference = today or datetime.now(UTC).date()
    start = _parse_date(params.get('from'), 'from') or _first_day_of_month(reference)
    end = _parse_date(params.get('to'), 'to') or _last_day_of_month(reference)
    if start > end:
        raise InvalidReportParameters('El parámetro from no puede ser posterior a to.')
    if _months_inclusive(start, end) > MAX_RANGE_MONTHS:
        raise InvalidReportParameters(
            f'El rango no puede superar los {MAX_RANGE_MONTHS} meses calendario.'
        )
    return ReportPeriod(start_date=start, end_date=end)


def _parse_date(raw: str | None, name: str) -> date | None:
    """Convierte un parámetro de fecha ISO, o None si no viene.

    Args:
        raw: valor crudo del parámetro.
        name: nombre del parámetro, para el mensaje de error.

    Returns:
        La fecha o None.

    Raises:
        InvalidReportParameters: si el valor no es una fecha ISO.
    """
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise InvalidReportParameters(f'El parámetro {name} no es una fecha ISO válida.') from exc


def _first_day_of_month(day: date) -> date:
    """Devuelve el primer día del mes de la fecha dada."""
    return day.replace(day=1)


def _last_day_of_month(day: date) -> date:
    """Devuelve el último día del mes de la fecha dada."""
    first_next = date(day.year + 1, 1, 1) if day.month == 12 else date(day.year, day.month + 1, 1)
    return first_next - timedelta(days=1)


def _months_inclusive(start: date, end: date) -> int:
    """Cantidad de meses calendario que cubre el rango, contando los dos extremos."""
    return (end.year - start.year) * 12 + (end.month - start.month) + 1
