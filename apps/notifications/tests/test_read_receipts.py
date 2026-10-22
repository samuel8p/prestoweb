"""Tests de los avisos leídos (notifications).

Un aviso se puede marcar como leído (una vez), todos los avisos se pueden
marcar de golpe y se puede saber cuántos quedan sin leer.
"""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def authenticate(client, email):
    """Registra un usuario y autentica al cliente con él."""
    from apps.identity.services import register_user

    user = register_user(email=email, password='TestPass123!')
    from rest_framework_simplejwt.tokens import RefreshToken

    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return user


def create_notification(user, event_type='budget_alert'):
    """Crea un aviso para el usuario."""
    return Notification.objects.create(
        user_id=user.id,
        event_type=event_type,
        reference_id=uuid.uuid4(),
        status=Notification.Status.SENT,
    )


def test_the_list_includes_the_read_at(client):
    """El listado de avisos trae el `read_at` (null si no se leyó)."""
    user = authenticate(client, 'leidos-lista@example.com')
    notification = create_notification(user)

    response = client.get('/api/v1/notifications/')

    assert response.status_code == 200
    result = response.json()['results'][0]
    assert result['id'] == str(notification.id)
    assert result['read_at'] is None


def test_a_notification_can_be_marked_as_read(client):
    """Un aviso propio se puede marcar como leído."""
    user = authenticate(client, 'leidos-uno@example.com')
    notification = create_notification(user)

    response = client.post(f'/api/v1/notifications/{notification.id}/read/')

    assert response.status_code == 200
    assert response.data['read_at'] is not None

    notification.refresh_from_db()
    assert notification.read_at is not None


def test_marking_a_notification_as_read_is_idempotent(client):
    """Marcarlo dos veces no cambia el `read_at` (ni falla)."""
    user = authenticate(client, 'leidos-idempotente@example.com')
    notification = create_notification(user)

    first = client.post(f'/api/v1/notifications/{notification.id}/read/')
    second = client.post(f'/api/v1/notifications/{notification.id}/read/')

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.data['read_at'] == second.data['read_at']


def test_the_notification_of_another_user_returns_404(client):
    """El aviso de otro usuario no se puede marcar (404)."""
    authenticate(client, 'leidos-ajeno@example.com')
    other_client = APIClient()
    other_user = authenticate(other_client, 'leidos-dueño@example.com')
    notification = create_notification(other_user)

    response = client.post(f'/api/v1/notifications/{notification.id}/read/')

    assert response.status_code == 404
    assert response.data['error']['code'] == 'not_found'


def test_all_the_notifications_can_be_marked_as_read(client):
    """Se pueden marcar todos los avisos del usuario de una vez."""
    user = authenticate(client, 'leidos-todos@example.com')
    first = create_notification(user)
    second = create_notification(user, 'installment_due_soon')

    response = client.post('/api/v1/notifications/read-all/')

    assert response.status_code == 200
    assert response.data['count'] == 2

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.read_at is not None
    assert second.read_at is not None


def test_marking_all_as_read_does_not_touch_the_notifications_of_another_user(client):
    """Los avisos de otro usuario no se tocan."""
    authenticate(client, 'leidos-aislado@example.com')
    other_client = APIClient()
    other_user = authenticate(other_client, 'leidos-otro-aislado@example.com')
    other_notification = create_notification(other_user)

    client.post('/api/v1/notifications/read-all/')

    other_notification.refresh_from_db()
    assert other_notification.read_at is None


def test_marking_all_as_read_is_idempotent(client):
    """Marcar todos dos veces no cambia nada."""
    user = authenticate(client, 'leidos-todos-idem@example.com')
    create_notification(user)

    first = client.post('/api/v1/notifications/read-all/')
    second = client.post('/api/v1/notifications/read-all/')

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.data['count'] == 0


def test_the_unread_count_is_returned(client):
    """El endpoint de no leídos devuelve el conteo."""
    user = authenticate(client, 'leidos-conteo@example.com')
    create_notification(user)
    create_notification(user, 'installment_due_soon')

    response = client.get('/api/v1/notifications/unread-count/')

    assert response.status_code == 200
    assert response.data == {'count': 2}

    notification = Notification.objects.filter(user_id=user.id).first()
    client.post(f'/api/v1/notifications/{notification.id}/read/')

    response = client.get('/api/v1/notifications/unread-count/')

    assert response.data == {'count': 1}


def test_the_unread_count_does_not_count_the_notifications_of_another_user(client):
    """El conteo solo mira los avisos del usuario."""
    authenticate(client, 'leidos-conteo-ajeno@example.com')
    other_client = APIClient()
    other_user = authenticate(other_client, 'leidos-conteo-otro@example.com')
    create_notification(other_user)

    response = client.get('/api/v1/notifications/unread-count/')

    assert response.data == {'count': 0}


def test_the_unread_count_needs_the_token(client):
    """Sin token, el conteo responde 401."""
    response = APIClient().get('/api/v1/notifications/unread-count/')

    assert response.status_code == 401


def test_the_unread_count_does_not_query_per_notification(client):
    """El conteo no hace una consulta por aviso."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    user = authenticate(client, 'leidos-consultas@example.com')
    for _ in range(5):
        create_notification(user)

    with CaptureQueriesContext(connection) as queries:
        response = client.get('/api/v1/notifications/unread-count/')

    assert response.status_code == 200
    assert len(queries) <= 2, f'consultas de más: {len(queries)}'
