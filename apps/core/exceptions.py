class DomainError(Exception):
    """Error de dominio general."""
    pass


class InsufficientFunds(DomainError):
    """Saldos insuficientes para la operación."""
    pass


class InvalidAmount(DomainError):
    """Monto inválido (negativo o cero)."""
    pass


class KYCNotCompleted(DomainError):
    """El usuario no tiene KYC completado."""
    pass