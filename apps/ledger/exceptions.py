"""Excepciones de dominio de la app ledger."""

from apps.core.exceptions import DomainError


class LedgerError(DomainError):
    """Error de dominio del ledger."""


class AccountNotFound(LedgerError):
    """La cuenta solicitada no existe o no pertenece al usuario."""


class AccountKindNotAllowed(LedgerError):
    """La cuenta no es del tipo requerido para la operación."""


class CurrencyMismatch(LedgerError):
    """Las cuentas involucradas no comparten la misma moneda."""


class SameAccountTransfer(LedgerError):
    """El origen y el destino de una transferencia son la misma cuenta."""


class IdempotencyConflict(LedgerError):
    """La clave de idempotencia ya existe con un payload distinto."""


class SimulatedDepositsDisabled(LedgerError):
    """Los depósitos simulados están deshabilitados."""
