"""Excepciones de dominio de la app offers."""

from apps.core.exceptions import DomainError


class OffersError(DomainError):
    """Error de dominio de offers."""


class OfferNotFound(OffersError):
    """La oferta no existe o no pertenece al prestamista."""


class OfferNotEditable(OffersError):
    """La oferta no se puede modificar en su estado actual."""


class OfferNotAcceptable(OffersError):
    """La oferta no está activa y no se puede aceptar."""


class CannotAcceptOwnOffer(OffersError):
    """El prestamista no puede aceptar su propia oferta."""
