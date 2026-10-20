"""Tests del permiso IsKycApproved (AGENTS §9.9)."""

import pytest
from rest_framework.test import APIRequestFactory

from apps.identity.tests.factories import KYCVerificationFactory, UserFactory

pytestmark = pytest.mark.django_db


def build_request(user):
    """Arma un request DRF con el usuario dado."""
    request = APIRequestFactory().get('/api/v1/kyc/')
    request.user = user
    return request


def test_permission_allows_approved_user():
    """Un usuario con KYC aprobada pasa el permiso."""
    from apps.identity.permissions import IsKycApproved

    user = UserFactory()
    KYCVerificationFactory(user=user, status='approved')

    assert IsKycApproved().has_permission(build_request(user), None) is True


def test_permission_denies_pending_user():
    """Un usuario con KYC pendiente no pasa el permiso."""
    from apps.identity.permissions import IsKycApproved

    user = UserFactory()
    KYCVerificationFactory(user=user, status='pending')

    assert IsKycApproved().has_permission(build_request(user), None) is False


def test_permission_denies_anonymous_user():
    """Un usuario anónimo no pasa el permiso."""
    from django.contrib.auth.models import AnonymousUser

    from apps.identity.permissions import IsKycApproved

    request = build_request(AnonymousUser())

    assert IsKycApproved().has_permission(request, None) is False
