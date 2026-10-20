"""Tests de los servicios de escritura de identity."""

import uuid

import pytest

from apps.identity.tests.factories import KYCVerificationFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_register_user_creates_user_with_profile():
    """El registro crea el usuario y su perfil vacío."""
    from apps.identity.services import register_user

    user = register_user(email='nuevo@example.com', password='TestPass123!')

    assert user.email == 'nuevo@example.com'
    assert user.check_password('TestPass123!')
    assert user.profile.phone_number == ''


def test_register_user_rejects_duplicate_email():
    """No se puede registrar dos veces el mismo email."""
    from apps.identity.exceptions import EmailAlreadyRegistered
    from apps.identity.services import register_user

    register_user(email='duplicado@example.com', password='TestPass123!')

    with pytest.raises(EmailAlreadyRegistered):
        register_user(email='duplicado@example.com', password='TestPass123!')


def test_submit_kyc_creates_pending_verification():
    """La solicitud de KYC queda en estado pending."""
    from apps.identity.services import submit_kyc

    user = UserFactory()
    verification = submit_kyc(user=user, documents={'front': 'passport.jpg'})

    assert verification.status == 'pending'
    assert verification.user == user
    assert verification.documents == {'front': 'passport.jpg'}


def test_submit_kyc_rejects_second_pending_verification():
    """Un usuario con verificación pendiente no puede volver a solicitar."""
    from apps.identity.exceptions import PendingKYCExists
    from apps.identity.services import submit_kyc

    user = UserFactory()
    submit_kyc(user=user, documents={})

    with pytest.raises(PendingKYCExists):
        submit_kyc(user=user, documents={})


def test_submit_kyc_rejects_non_mapping_documents():
    """Los documentos deben ser un objeto JSON de metadata."""
    from apps.identity.exceptions import InvalidDocuments
    from apps.identity.services import submit_kyc

    user = UserFactory()

    with pytest.raises(InvalidDocuments):
        submit_kyc(user=user, documents=['no', 'es', 'un', 'objeto'])


def test_resolve_kyc_approves_and_records_resolver():
    """La aprobación deja el estado, la fecha y el resolutor registrados."""
    from apps.identity.services import resolve_kyc

    user = UserFactory()
    verification = KYCVerificationFactory(user=user)
    resolver_id = uuid.uuid4()

    resolved = resolve_kyc(
        verification_id=verification.id,
        status='approved',
        resolved_by_user_id=resolver_id,
    )

    assert resolved.status == 'approved'
    assert resolved.resolved_at is not None
    assert resolved.resolved_by_user_id == resolver_id


def test_resolve_kyc_rejects_already_resolved_verification():
    """Una verificación ya resuelta no se puede volver a resolver."""
    from apps.identity.exceptions import KYCAlreadyResolved
    from apps.identity.services import resolve_kyc

    verification = KYCVerificationFactory(status='approved')

    with pytest.raises(KYCAlreadyResolved):
        resolve_kyc(
            verification_id=verification.id,
            status='rejected',
            resolved_by_user_id=uuid.uuid4(),
        )


def test_resolve_kyc_rejects_invalid_status():
    """Solo se puede resolver a approved o rejected."""
    from apps.identity.exceptions import InvalidKYCResolution
    from apps.identity.services import resolve_kyc

    verification = KYCVerificationFactory()

    with pytest.raises(InvalidKYCResolution):
        resolve_kyc(
            verification_id=verification.id,
            status='pending',
            resolved_by_user_id=uuid.uuid4(),
        )


def test_resolve_kyc_logs_decision_without_sensitive_data(caplog):
    """La resolución queda auditada en logs sin datos sensibles."""
    import logging

    from apps.identity.services import resolve_kyc

    user = UserFactory()
    verification = KYCVerificationFactory(user=user)
    resolver_id = uuid.uuid4()

    with caplog.at_level(logging.INFO):
        resolve_kyc(
            verification_id=verification.id,
            status='approved',
            resolved_by_user_id=resolver_id,
        )

    records = [record for record in caplog.records if 'kyc' in record.getMessage().lower()]
    assert records
    message = records[0].getMessage()
    assert str(user.id) in message
    assert str(resolver_id) in message
    assert 'documents' not in message
