"""Permisos de la app offers."""

from rest_framework.permissions import BasePermission

from apps.identity.selectors import is_kyc_approved


class HasApprovedKyc(BasePermission):
    """Permite publicar y modificar ofertas solo con KYC aprobada.

    El control equivalente en la capa de servicios sigue vigente: este
    permiso evita el viaje de red cuando el usuario no cumple el requisito.
    """

    message = 'Necesitás completar la verificación KYC para publicar ofertas.'

    def has_permission(self, request, view) -> bool:
        """True solo si el usuario autenticado tiene KYC aprobada."""
        user = request.user
        return bool(user and user.is_authenticated and is_kyc_approved(user_id=user.id))
