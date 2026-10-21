"""Excepciones de dominio de la app reports."""

from apps.core.exceptions import DomainError


class ReportsError(DomainError):
    """Error de dominio de reports."""


class InvalidReportParameters(ReportsError):
    """Los parámetros del reporte no son válidos."""


class ReportTooLarge(ReportsError):
    """El reporte supera el tope de filas exportables."""
