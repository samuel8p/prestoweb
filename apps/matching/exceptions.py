"""Excepciones de dominio de la app matching."""

from apps.core.exceptions import DomainError


class MatchingError(DomainError):
    """Error de dominio de matching."""


class NotEnoughOffersToCompare(MatchingError):
    """Hacen falta al menos dos ofertas para comparar."""


class OfferNotFound(MatchingError):
    """La oferta no existe o no está activa."""
