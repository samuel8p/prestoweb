"""Tests de la API de notifications."""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def create_user(email='notificaciones@example.com'):
    """Crea un usuario con KYC aprobada."""
    from apps.identity.services import register_user, resolve_kyc, submit_kyc

    user = register_user(email=email, password='TestPass123!')
    verification = submit_kyc(user=user, documents={})
    resolve_kyc(
        verification_id=verification.id,
        status='approved',
        resolved_by_user_id=None,
    )
    return user


def authenticate(client, user):
    """Autentica al cliente con un access token del usuario dado."""
    from rest_framework_simplejwt.tokens import RefreshToken

    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


def test_notifications_list_requires_authentication(client):
    """Sin token el listado responde 401."""
    response = client.get('/api/v1/notifications/')

    assert response.status_code == 401
    assert response.data['error']['code'] == 'not_authenticated'


def test_preferences_require_authentication(client):
    """Sin token las preferencias responden 401."""
    assert client.get('/api/v1/notifications/preferences/').status_code == 401
    assert client.put('/api/v1/notifications/preferences/', {}, format='json').status_code == 401


def test_notifications_list_returns_only_own_notifications(client):
    """Cada usuario ve solo sus avisos."""
    from apps.notifications.tests.factories import NotificationFactory

    user = create_user()
    other = create_user(email='notificaciones-otro@example.com')
    NotificationFactory(user_id=user.id, event_type='installment_due_soon')
    NotificationFactory(user_id=other.id, event_type='installment_due_soon')
    authenticate(client, user)

    response = client.get('/api/v1/notifications/')

    assert response.status_code == 200
    assert response.data['count'] == 1
    assert response.data['results'][0]['user_id'] == str(user.id)


def test_preferences_get_returns_every_event_enabled_by_default(client):
    """El listado de preferencias trae todos los eventos."""
    user = create_user()
    authenticate(client, user)

    response = client.get('/api/v1/notifications/preferences/')

    assert response.status_code == 200
    event_types = {preference['event_type'] for preference in response.data['preferences']}
    assert event_types == set(Notification.EventType.values)
    assert all(preference['enabled'] for preference in response.data['preferences'])


def test_preferences_put_disables_an_event(client):
    """El PUT desactiva un evento y el GET lo refleja."""
    user = create_user()
    authenticate(client, user)

    response = client.put(
        '/api/v1/notifications/preferences/',
        {'event_type': Notification.EventType.BUDGET_ALERT, 'enabled': False},
        format='json',
    )

    assert response.status_code == 200
    assert response.data['event_type'] == Notification.EventType.BUDGET_ALERT
    assert response.data['enabled'] is False

    listed = client.get('/api/v1/notifications/preferences/')
    preferences = {item['event_type']: item['enabled'] for item in listed.data['preferences']}
    assert preferences[Notification.EventType.BUDGET_ALERT] is False


def test_preferences_put_rejects_an_unknown_event(client):
    """Un evento que no es del proyecto devuelve 400."""
    user = create_user()
    authenticate(client, user)

    response = client.put(
        '/api/v1/notifications/preferences/',
        {'event_type': 'evento_inventado', 'enabled': False},
        format='json',
    )

    assert response.status_code == 400


def test_preferences_are_isolated_between_users(client):
    """La preferencia de un usuario no afecta al otro."""
    user = create_user()
    other = create_user(email='notificaciones-preferencias-otro@example.com')
    authenticate(client, user)
    client.put(
        '/api/v1/notifications/preferences/',
        {'event_type': Notification.EventType.INVESTMENT_SETTLED, 'enabled': False},
        format='json',
    )
    client.credentials()
    authenticate(client, other)

    response = client.get('/api/v1/notifications/preferences/')

    preferences = {item['event_type']: item['enabled'] for item in response.data['preferences']}
    assert preferences[Notification.EventType.INVESTMENT_SETTLED] is True
