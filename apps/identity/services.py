"""Servicios de escritura de la app identity (interfaz pública)."""

import logging
import uuid
from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.identity.exceptions import (
    EmailAlreadyRegistered,
    InvalidDocuments,
    InvalidKYCResolution,
    InvalidProfileField,
    KYCAlreadyResolved,
    PendingKYCExists,
    WeakPassword,
)
from apps.identity.models import KYCVerification, Profile, User

logger = logging.getLogger(__name__)

RESOLVABLE_STATUSES = (KYCVerification.Status.APPROVED, KYCVerification.Status.REJECTED)
PROFILE_FIELDS = ('phone_number', 'date_of_birth', 'country')


def register_user(email: str, password: str) -> User:
    """Registra un usuario y le crea su perfil vacío.

    Args:
        email: email único del usuario.
        password: contraseña en texto plano; se hashea antes de guardar.

    Returns:
        El usuario creado, con su perfil asociado.

    Raises:
        EmailAlreadyRegistered: si ya existe un usuario con ese email.
        WeakPassword: si la contraseña no pasa los validadores de Django.
    """
    if User.objects.filter(email__iexact=email).exists():
        raise EmailAlreadyRegistered('Ya existe un usuario registrado con ese email.')
    try:
        validate_password(password)
    except DjangoValidationError as exc:
        raise WeakPassword('; '.join(exc.messages)) from exc
    with transaction.atomic():
        user = User.objects.create_user(email=email, password=password)
        Profile.objects.create(user=user)
    logger.info('Usuario registrado: user_id=%s', user.id)
    return user


def submit_kyc(user: User, documents: dict[str, Any]) -> KYCVerification:
    """Registra una solicitud de verificación KYC para un usuario.

    Args:
        user: usuario que solicita la verificación.
        documents: metadata de los documentos (objeto JSON).

    Returns:
        La verificación creada, en estado pending.

    Raises:
        InvalidDocuments: si documents no es un objeto JSON.
        PendingKYCExists: si el usuario ya tiene una verificación pendiente.
    """
    if not isinstance(documents, dict):
        raise InvalidDocuments('Los documentos deben enviarse como objeto JSON de metadata.')
    try:
        with transaction.atomic():
            verification = KYCVerification.objects.create(user=user, documents=documents)
    except IntegrityError as exc:
        raise PendingKYCExists('El usuario ya tiene una verificación KYC pendiente.') from exc
    logger.info(
        'Verificación KYC solicitada: user_id=%s verification_id=%s', user.id, verification.id
    )
    return verification


def resolve_kyc(
    verification_id: uuid.UUID,
    status: str,
    resolved_by_user_id: uuid.UUID,
) -> KYCVerification:
    """Resuelve una verificación KYC aprobándola o rechazándola.

    Args:
        verification_id: identificador de la verificación a resolver.
        status: `approved` o `rejected`.
        resolved_by_user_id: identificador del usuario que decide.

    Returns:
        La verificación resuelta.

    Raises:
        InvalidKYCResolution: si el estado no es `approved` ni `rejected`.
        KYCAlreadyResolved: si la verificación ya había sido resuelta.
    """
    if status not in RESOLVABLE_STATUSES:
        raise InvalidKYCResolution(
            'Una verificación KYC solo puede resolverse como approved o rejected.'
        )
    with transaction.atomic():
        verification = KYCVerification.objects.select_for_update().get(pk=verification_id)
        if verification.status != KYCVerification.Status.PENDING:
            raise KYCAlreadyResolved('La verificación KYC ya fue resuelta.')
        verification.status = status
        verification.resolved_at = timezone.now()
        verification.resolved_by_user_id = resolved_by_user_id
        verification.save(update_fields=['status', 'resolved_at', 'resolved_by_user_id'])
    logger.info(
        'Verificación KYC resuelta: user_id=%s verification_id=%s status=%s resolved_by_user_id=%s',
        verification.user_id,
        verification.id,
        status,
        resolved_by_user_id,
    )
    return verification


def update_profile(user: User, changes: dict[str, Any]) -> Profile:
    """Actualiza los campos del perfil de un usuario, creándolo si no existe.

    Args:
        user: usuario dueño del perfil.
        changes: campos a actualizar (phone_number, date_of_birth, country).

    Returns:
        El perfil actualizado.

    Raises:
        InvalidProfileField: si se intenta modificar un campo ajeno al perfil.
    """
    unknown_fields = set(changes) - set(PROFILE_FIELDS)
    if unknown_fields:
        raise InvalidProfileField('Ese campo no pertenece al perfil del usuario.')
    profile, _ = Profile.objects.get_or_create(user=user)
    for field, value in changes.items():
        setattr(profile, field, value)
    profile.full_clean()
    profile.save()
    return profile
