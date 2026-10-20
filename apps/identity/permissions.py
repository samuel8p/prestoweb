"""Permisos y límites de tasa de la app identity."""

from rest_framework.permissions import BasePermission
from rest_framework.throttling import ScopedRateThrottle

from apps.identity.selectors import is_kyc_approved


class LoginThrottle(ScopedRateThrottle):
    """Limita los intentos de login a 5 por minuto (AGENTS §9.6).

    El scope lo define la vista con `throttle_scope = 'login'`.
    """


class RegisterThrottle(ScopedRateThrottle):
    """Limita los registros a 5 por hora (AGENTS §9.6).

    El scope lo define la vista con `throttle_scope = 'register'`.
    """


class IsKycApproved(BasePermission):
    """Permite el acceso solo a usuarios con verificación KYC aprobada (AGENTS §9.9)."""

    message = 'Necesitás completar la verificación KYC para realizar esta operación.'

    def has_permission(self, request, view) -> bool:
        """Devuelve True solo si el usuario autenticado tiene KYC aprobada."""
        user = request.user
        return bool(user and user.is_authenticated and is_kyc_approved(user_id=user.id))
