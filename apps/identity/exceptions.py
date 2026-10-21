"""Excepciones de dominio de la app identity."""

from apps.core.exceptions import DomainError


class IdentityError(DomainError):
    """Error de dominio de identity."""


class EmailAlreadyRegistered(IdentityError):
    """El email ya está registrado."""


class PendingKYCExists(IdentityError):
    """El usuario ya tiene una verificación KYC pendiente."""


class KYCAlreadyResolved(IdentityError):
    """La verificación KYC ya fue resuelta."""


class InvalidKYCResolution(IdentityError):
    """La resolución de KYC no es válida."""


class InvalidDocuments(IdentityError):
    """Los documentos enviados no son un objeto JSON de metadata."""


class InvalidProfileField(IdentityError):
    """Se intentó modificar un campo que no pertenece al perfil."""


class WeakPassword(IdentityError):
    """La contraseña no pasa los validadores de Django."""
