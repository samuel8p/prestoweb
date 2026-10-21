"""Excepciones de dominio de la app loans."""

from apps.core.exceptions import DomainError


class LoansError(DomainError):
    """Error de dominio de loans."""


class LoanNotFound(LoansError):
    """El préstamo no existe."""


class NotTheBorrower(LoansError):
    """Solo el prestatario puede pagar las cuotas."""


class InstallmentOutOfOrder(LoansError):
    """Las cuotas se pagan en orden."""


class InstallmentAlreadyPaid(LoansError):
    """La cuota ya está pagada."""


class InvalidLoanTransition(LoansError):
    """La transición de estado del préstamo no es válida."""
