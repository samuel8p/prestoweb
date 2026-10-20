"""Tests del manejador de errores uniforme de la API (AGENTS §8)."""

import pytest


def test_validation_error_uses_agenda_format():
    """Un error de validación devuelve error.code, error.message y error.details."""
    from rest_framework.exceptions import ValidationError

    from apps.core.exception_handler import api_exception_handler

    response = api_exception_handler(ValidationError({'email': ['Este campo es requerido.']}), {})

    assert response is not None
    assert response.status_code == 400
    assert set(response.data['error']) == {'code', 'message', 'details'}
    assert response.data['error']['code'] == 'validation_error'
    assert response.data['error']['details'] == {'email': ['Este campo es requerido.']}
    assert response.data['error']['message']


def test_not_found_uses_agenda_format():
    """Un 404 devuelve el mensaje original y el código not_found."""
    from rest_framework.exceptions import NotFound

    from apps.core.exception_handler import api_exception_handler

    response = api_exception_handler(NotFound('No existe el recurso.'), {})

    assert response.status_code == 404
    assert response.data['error']['code'] == 'not_found'
    assert response.data['error']['message'] == 'No existe el recurso.'
    assert response.data['error']['details'] == {}


def test_not_authenticated_uses_agenda_format():
    """Un 401 devuelve el código not_authenticated."""
    from rest_framework.exceptions import NotAuthenticated

    from apps.core.exception_handler import api_exception_handler

    response = api_exception_handler(NotAuthenticated(), {})

    assert response.status_code == 401
    assert response.data['error']['code'] == 'not_authenticated'
    assert response.data['error']['message']


def test_permission_denied_uses_agenda_format():
    """Un 403 devuelve el código permission_denied."""
    from rest_framework.exceptions import PermissionDenied

    from apps.core.exception_handler import api_exception_handler

    response = api_exception_handler(PermissionDenied(), {})

    assert response.status_code == 403
    assert response.data['error']['code'] == 'permission_denied'


def test_non_api_exception_is_not_handled():
    """Las excepciones que no son de API se dejan propagar."""
    from apps.core.exception_handler import api_exception_handler

    assert api_exception_handler(ValueError('boom'), {}) is None
