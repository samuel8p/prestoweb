"""Selectores de lectura de la app identity (interfaz pública)."""

import uuid

from apps.identity.models import KYCVerification, Profile


def get_profile(user_id: uuid.UUID) -> Profile | None:
    """Devuelve el perfil del usuario, o None si no tiene.

    Args:
        user_id: identificador del usuario.

    Returns:
        El Profile del usuario o None.
    """
    return Profile.objects.filter(user_id=user_id).first()


def get_kyc_for_user(user_id: uuid.UUID) -> KYCVerification | None:
    """Devuelve la verificación KYC más reciente del usuario.

    Args:
        user_id: identificador del usuario.

    Returns:
        La KYCVerification más reciente o None.
    """
    return KYCVerification.objects.filter(user_id=user_id).order_by('-requested_at').first()


def get_kyc_by_id(verification_id: uuid.UUID, user_id: uuid.UUID) -> KYCVerification | None:
    """Devuelve una verificación KYC solo si pertenece al usuario indicado.

    Args:
        verification_id: identificador de la verificación.
        user_id: identificador del usuario propietario.

    Returns:
        La KYCVerification o None si no existe o es de otro usuario.
    """
    return KYCVerification.objects.filter(pk=verification_id, user_id=user_id).first()


def is_kyc_approved(user_id: uuid.UUID) -> bool:
    """Indica si la verificación KYC vigente del usuario está aprobada.

    Args:
        user_id: identificador del usuario.

    Returns:
        True solo si la verificación más reciente está en estado approved.
    """
    verification = get_kyc_for_user(user_id=user_id)
    return verification is not None and verification.status == KYCVerification.Status.APPROVED
