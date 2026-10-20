"""Tests de la administración de Django para la app identity."""

import uuid

import pytest
from django.test import Client

from apps.identity.tests.factories import KYCVerificationFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_admin_approve_action_resolves_selected_verifications(admin_client):
    """La acción de admin aprueba las verificaciones seleccionadas."""
    user = UserFactory()
    verification = KYCVerificationFactory(user=user)

    response = admin_client.post(
        '/admin/identity/kycverification/',
        {
            'action': 'approve_kyc',
            '_selected_action': [str(verification.id)],
        },
        follow=True,
    )

    assert response.status_code == 200
    verification.refresh_from_db()
    assert verification.status == 'approved'
    assert verification.resolved_by_user_id == uuid.UUID(admin_client.session['_auth_user_id'])


def test_admin_reject_action_resolves_selected_verifications(admin_client):
    """La acción de admin rechaza las verificaciones seleccionadas."""
    user = UserFactory()
    verification = KYCVerificationFactory(user=user)

    admin_client.post(
        '/admin/identity/kycverification/',
        {
            'action': 'reject_kyc',
            '_selected_action': [str(verification.id)],
        },
        follow=True,
    )

    verification.refresh_from_db()
    assert verification.status == 'rejected'


def test_admin_action_skips_already_resolved_verifications(admin_client):
    """La acción de admin no rompe con verificaciones ya resueltas."""
    user = UserFactory()
    verification = KYCVerificationFactory(user=user, status='approved')

    response = admin_client.post(
        '/admin/identity/kycverification/',
        {
            'action': 'reject_kyc',
            '_selected_action': [str(verification.id)],
        },
        follow=True,
    )

    assert response.status_code == 200
    verification.refresh_from_db()
    assert verification.status == 'approved'


def test_admin_only_staff_can_access_verifications():
    """Un usuario sin permisos de staff no accede al admin."""
    client = Client()
    client.force_login(UserFactory())

    response = client.get('/admin/identity/kycverification/')

    assert response.status_code in (302, 403)
