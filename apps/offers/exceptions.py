"""Excepciones de dominio de la app offers."""

from apps.core.exceptions import DomainError


class OffersError(DomainError):
    """Error de dominio de offers."""


class OfferNotFound(OffersError):
    """La oferta no existe o no pertenece al prestamista."""


class OfferNotEditable(OffersError):
    """La oferta no se puede modificar en su estado actual."""
