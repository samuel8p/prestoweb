"""Tests de los selectores de lectura de identity."""

import pytest

from apps.identity.tests.factories import KYCVerificationFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_get_profile_returns_profile():
    """El selector devuelve el perfil del usuario."""
    from apps.identity.selectors import get_profile
    from apps.identity.services import register_user

    user = register_user(email='perfil@example.com', password='TestPass123!')

    profile = get_profile(user_id=user.id)

    assert profile is not None
    assert profile.user_id == user.id


def test_get_profile_returns_none_when_missing():
    """El selector devuelve None si el usuario no tiene perfil."""
    from apps.identity.selectors import get_profile

    user = UserFactory()

    assert get_profile(user_id=user.id) is None


def test_get_kyc_for_user_returns_latest_verification():
    """El selector devuelve la verificación más reciente."""
    from apps.identity.selectors import get_kyc_for_user

    user = UserFactory()
    KYCVerificationFactory(user=user, status='rejected')
    latest = KYCVerificationFactory(user=user, status='pending')

    verification = get_kyc_for_user(user_id=user.id)

    assert verification is not None
    assert verification.id == latest.id


def test_get_kyc_for_user_returns_none_when_missing():
    """El selector devuelve None si el usuario no tiene verificaciones."""
    from apps.identity.selectors import get_kyc_for_user

    user = UserFactory()

    assert get_kyc_for_user(user_id=user.id) is None


def test_is_kyc_approved_true_for_approved_user():
    """Un usuario con verificación aprobada está aprobado."""
    from apps.identity.selectors import is_kyc_approved

    user = UserFactory()
    KYCVerificationFactory(user=user, status='approved')

    assert is_kyc_approved(user_id=user.id) is True


def test_is_kyc_approved_false_for_pending_user():
    """Un usuario con verificación pendiente no está aprobado."""
    from apps.identity.selectors import is_kyc_approved

    user = UserFactory()
    KYCVerificationFactory(user=user, status='pending')

    assert is_kyc_approved(user_id=user.id) is False


def test_is_kyc_approved_false_for_rejected_user():
    """Un usuario con verificación rechazada no está aprobado."""
    from apps.identity.selectors import is_kyc_approved

    user = UserFactory()
    KYCVerificationFactory(user=user, status='rejected')

    assert is_kyc_approved(user_id=user.id) is False


def test_is_kyc_approved_false_without_verifications():
    """Un usuario sin verificaciones no está aprobado."""
    from apps.identity.selectors import is_kyc_approved

    user = UserFactory()

    assert is_kyc_approved(user_id=user.id) is False


def test_is_kyc_approved_follows_latest_verification():
    """Si la verificación más reciente no está aprobada, el usuario no lo está."""
    from apps.identity.selectors import is_kyc_approved

    user = UserFactory()
    KYCVerificationFactory(user=user, status='approved')
    KYCVerificationFactory(user=user, status='rejected')

    assert is_kyc_approved(user_id=user.id) is False


def test_get_kyc_by_id_returns_own_verification():
    """El selector de detalle devuelve la verificación del propio usuario."""
    from apps.identity.selectors import get_kyc_by_id

    user = UserFactory()
    verification = KYCVerificationFactory(user=user)

    found = get_kyc_by_id(verification_id=verification.id, user_id=user.id)

    assert found is not None
    assert found.id == verification.id


def test_get_kyc_by_id_returns_none_for_other_user():
    """El selector de detalle no expone verificaciones de otros usuarios."""
    from apps.identity.selectors import get_kyc_by_id

    other = UserFactory()
    verification = KYCVerificationFactory(user=other)
    user = UserFactory()

    assert get_kyc_by_id(verification_id=verification.id, user_id=user.id) is None
