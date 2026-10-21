"""Tests del CORS: el front en Vercel tiene que poder llamar a la API.

El backend es API only y el front vive en otro origen, así que la API
responde con los headers de CORS. Las reglas:

- solo los orígenes de `CORS_ALLOWED_ORIGINS` reciben permiso;
- nunca se refleja `*`;
- sin orígenes configurados, no hay CORS;
- las credenciales (cookies) no se permiten: la autenticación es por
  `Authorization: Bearer`.
"""

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

ORIGEN_PERMITIDO = 'https://presto-front.vercel.app'
ORIGEN_AJENO = 'https://otro-sitio.example'


@pytest.fixture
def client():
    return APIClient()


def test_an_allowed_origin_receives_the_cors_header(client):
    """Un origen de la lista recibe `Access-Control-Allow-Origin`."""
    with override_settings(CORS_ALLOWED_ORIGINS=[ORIGEN_PERMITIDO]):
        response = client.get('/api/v1/meta/', HTTP_ORIGIN=ORIGEN_PERMITIDO)

    assert response.status_code == 200
    assert response['Access-Control-Allow-Origin'] == ORIGEN_PERMITIDO


def test_an_origin_outside_the_list_does_not_receive_the_header(client):
    """Un origen que no está en la lista no recibe permiso alguno."""
    with override_settings(CORS_ALLOWED_ORIGINS=[ORIGEN_PERMITIDO]):
        response = client.get('/api/v1/meta/', HTTP_ORIGIN=ORIGEN_AJENO)

    assert response.status_code == 200
    assert 'Access-Control-Allow-Origin' not in response


def test_a_request_without_origin_receives_no_cors_header(client):
    """Una petición sin `Origin` (el front no, curl sí) no lleva headers de CORS."""
    with override_settings(CORS_ALLOWED_ORIGINS=[ORIGEN_PERMITIDO]):
        response = client.get('/api/v1/meta/')

    assert 'Access-Control-Allow-Origin' not in response


def test_the_preflight_request_is_answered(client):
    """El preflight `OPTIONS` de un método con credenciales se responde."""
    with override_settings(CORS_ALLOWED_ORIGINS=[ORIGEN_PERMITIDO]):
        response = client.options(
            '/api/v1/ledger/transactions/',
            HTTP_ORIGIN=ORIGEN_PERMITIDO,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization,content-type',
        )

    assert response.status_code in (200, 204)
    assert response['Access-Control-Allow-Origin'] == ORIGEN_PERMITIDO
    assert 'POST' in response['Access-Control-Allow-Methods']


def test_the_preflight_allows_the_authorization_header(client):
    """El header `Authorization` (el token JWT) está permitido."""
    with override_settings(CORS_ALLOWED_ORIGINS=[ORIGEN_PERMITIDO]):
        response = client.options(
            '/api/v1/ledger/transactions/',
            HTTP_ORIGIN=ORIGEN_PERMITIDO,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization',
        )

    assert 'authorization' in response['Access-Control-Allow-Headers'].lower()


def test_the_response_never_reflects_a_wildcard(client):
    """La respuesta nunca devuelve `*` como origen permitido."""
    with override_settings(CORS_ALLOWED_ORIGINS=[ORIGEN_PERMITIDO]):
        response = client.get('/api/v1/meta/', HTTP_ORIGIN=ORIGEN_PERMITIDO)

    assert response['Access-Control-Allow-Origin'] != '*'


def test_without_configured_origins_there_is_no_cors(client):
    """Sin orígenes configurados, la API no responde con headers de CORS."""
    with override_settings(CORS_ALLOWED_ORIGINS=[]):
        response = client.get('/api/v1/meta/', HTTP_ORIGIN=ORIGEN_PERMITIDO)

    assert 'Access-Control-Allow-Origin' not in response


def test_credentials_are_not_allowed(client):
    """No se permiten credenciales: la autenticación va en `Authorization`."""
    with override_settings(CORS_ALLOWED_ORIGINS=[ORIGEN_PERMITIDO]):
        response = client.get('/api/v1/meta/', HTTP_ORIGIN=ORIGEN_PERMITIDO)

    assert 'Access-Control-Allow-Credentials' not in response
