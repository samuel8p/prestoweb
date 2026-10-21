"""Tests del permiso HasApprovedKyc de la app offers."""

import uuid

import pytest
from rest_framework.test import APIRequestFactory

from apps.offers.tests.factories import create_approved_user

pytestmark = pytest.mark.django_db


def build_request(user):
    """Arma un request DRF con el usuario dado."""
    request = APIRequestFactory().post('/api/v1/offers/')
    request.user = user
    return request


def test_permission_allows_user_with_approved_kyc():
    """Un prestamista con KYC aprobada pasa el permiso."""
    from apps.offers.permissions import HasApprovedKyc

    user = create_approved_user()

    assert HasApprovedKyc().has_permission(build_request(user), None) is True


def test_permission_denies_user_without_kyc():
    """Un prestamista sin KYC aprobada no pasa el permiso."""
    from apps.identity.services import register_user
    from apps.offers.permissions import HasApprovedKyc

    user = register_user(email='sin-kyc-permiso@example.com', password='TestPass123!')

    assert HasApprovedKyc().has_permission(build_request(user), None) is False


def test_permission_denies_anonymous_user():
    """Un usuario anónimo no pasa el permiso."""
    from django.contrib.auth.models import AnonymousUser

    from apps.offers.permissions import HasApprovedKyc

    request = build_request(AnonymousUser())

    assert HasApprovedKyc().has_permission(request, None) is False


def test_permission_message_is_in_spanish():
    """El mensaje del permiso es legible y en español."""
    from apps.offers.permissions import HasApprovedKyc

    message = HasApprovedKyc().message

    assert 'KYC' in message
    assert message != uuid.uuid4().hex
