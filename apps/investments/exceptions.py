"""Excepciones de dominio de la app investments."""

from apps.core.exceptions import DomainError


class InvestmentsError(DomainError):
    """Error de dominio de investments."""


class ProductNotFound(InvestmentsError):
    """El producto de inversión no existe."""


class ProductNotActive(InvestmentsError):
    """El producto de inversión no admite nuevas posiciones."""


class InsufficientInvestmentAmount(InvestmentsError):
    """El monto es menor al mínimo del producto."""
