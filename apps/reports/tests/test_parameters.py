"""Tests de la validación de parámetros de los reportes."""

from datetime import UTC, date, datetime

import pytest

from apps.reports.exceptions import InvalidReportParameters


def test_parse_currency_returns_the_requested_currency():
    """La moneda del reporte se toma del parámetro `currency`."""
    from apps.reports.selectors import parse_currency

    assert parse_currency({'currency': 'ARS'}) == 'ARS'
    assert parse_currency({'currency': 'USD'}) == 'USD'


def test_parse_currency_requires_the_currency():
    """La moneda es obligatoria: un reporte nunca mezcla monedas."""
    from apps.reports.selectors import parse_currency

    with pytest.raises(InvalidReportParameters):
        parse_currency({})

    with pytest.raises(InvalidReportParameters):
        parse_currency({'currency': ''})


def test_parse_currency_rejects_an_unknown_currency():
    """Solo se aceptan las monedas del proyecto."""
    from apps.reports.selectors import parse_currency

    with pytest.raises(InvalidReportParameters):
        parse_currency({'currency': 'EUR'})


def test_parse_period_defaults_to_the_current_month():
    """Sin fechas, el reporte cubre el mes calendario actual en UTC."""
    from apps.reports.selectors import parse_period

    today = date(2026, 10, 21)
    period = parse_period({}, today=today)

    assert period.start_date == date(2026, 10, 1)
    assert period.end_date == date(2026, 10, 31)


def test_parse_period_reads_iso_dates():
    """Las fechas llegan en ISO (AAAA-MM-DD)."""
    from apps.reports.selectors import parse_period

    period = parse_period({'from': '2026-01-01', 'to': '2026-03-31'})

    assert period.start_date == date(2026, 1, 1)
    assert period.end_date == date(2026, 3, 31)


def test_parse_period_rejects_from_after_to():
    """`from` posterior a `to` es un error."""
    from apps.reports.selectors import parse_period

    with pytest.raises(InvalidReportParameters):
        parse_period({'from': '2026-03-01', 'to': '2026-01-31'})


def test_parse_period_rejects_a_range_longer_than_twelve_months():
    """El rango no puede cubrir más de 12 meses calendario."""
    from apps.reports.selectors import parse_period

    with pytest.raises(InvalidReportParameters):
        parse_period({'from': '2025-01-01', 'to': '2026-02-28'})


def test_parse_period_accepts_exactly_twelve_months():
    """Doce meses calendario entran."""
    from apps.reports.selectors import parse_period

    period = parse_period({'from': '2026-01-01', 'to': '2026-12-31'})

    assert period.start_date == date(2026, 1, 1)
    assert period.end_date == date(2026, 12, 31)


def test_parse_period_rejects_an_invalid_date():
    """Una fecha que no es ISO es un error."""
    from apps.reports.selectors import parse_period

    with pytest.raises(InvalidReportParameters):
        parse_period({'from': '01/01/2026'})

    with pytest.raises(InvalidReportParameters):
        parse_period({'to': 'ayer'})


def test_report_period_bounds_are_utc_datetimes():
    """El rango se traduce a datetimes UTC inclusivos."""
    from apps.reports.selectors import parse_period

    period = parse_period({'from': '2026-01-01', 'to': '2026-01-31'})

    assert period.start_datetime == datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    assert period.end_datetime == datetime(2026, 1, 31, 23, 59, 59, 999999, tzinfo=UTC)
