"""Tests del alias público del usuario (identity).

El alias es el identificador por el que un usuario puede ser encontrado (para
mandarle plata). Tiene reglas estrictas de formato y es único sin distinguir
mayúsculas.
"""

import uuid

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def register(client, email):
    """Registra un usuario y autentica al cliente con él."""
    from apps.identity.services import register_user

    user = register_user(email=email, password='TestPass123!')
    from rest_framework_simplejwt.tokens import RefreshToken

    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return user


def set_alias(client, alias):
    """Pone el alias del usuario autenticado."""
    return client.put('/api/v1/identity/alias/', {'alias': alias}, format='json')


def test_the_user_can_set_an_alias(client):
    """Un usuario puede poner su alias."""
    user = register(client, 'alias-uno@example.com')

    response = set_alias(client, 'juan.perez')

    assert response.status_code == 200
    assert response.data['alias'] == 'juan.perez'

    user.refresh_from_db()
    assert user.alias == 'juan.perez'


def test_the_user_can_change_the_alias(client):
    """El alias se puede cambiar (es propio)."""
    user = register(client, 'alias-cambio@example.com')
    set_alias(client, 'nombre.antiguo')

    response = set_alias(client, 'nombre.nuevo')

    assert response.status_code == 200
    assert response.data['alias'] == 'nombre.nuevo'

    user.refresh_from_db()
    assert user.alias == 'nombre.nuevo'


def test_an_alias_taken_by_another_user_returns_409(client):
    """Un alias que ya existe devuelve 409."""
    register(client, 'alias-tomado@example.com')
    set_alias(client, 'alias.tomado')

    other_client = APIClient()
    register(other_client, 'alias-otro@example.com')

    response = set_alias(other_client, 'alias.tomado')

    assert response.status_code == 409
    assert response.data['error']['code'] == 'alias_taken'


def test_the_uniqueness_ignores_the_case(client):
    """El alias es único sin distinguir mayúsculas."""
    from apps.identity.models import User

    user = register(client, 'alias-case@example.com')
    # Se escribe en mayúsculas directo en la base (el formato las rechaza en
    # la API, pero la base las.unique sin distinguir mayúsculas ✓).
    User.objects.filter(id=user.id).update(alias='Alias.Case')

    other_client = APIClient()
    register(other_client, 'alias-case-otro@example.com')

    response = set_alias(other_client, 'alias.case')

    assert response.status_code == 409


@pytest.mark.parametrize(
    'alias',
    [
        'corto',  # menos de 6
        'a' * 21,  # más de 20
        'con espacios',
        'ConMayusculas',
        'con.acentú',
        'con@arroba',
        '-empieza-con-guion',
        'termina-con-guion-',
        '.empieza-con-punto',
        'termina-con-punto.',
        'espacio interior',
        '',
    ],
)
def test_an_invalid_alias_returns_400(client, alias):
    """Un alias con un formato inválido devuelve 400."""
    register(client, f'alias-invalido-{uuid.uuid4().hex[:6]}@example.com')

    response = set_alias(client, alias)

    assert response.status_code == 400
    assert response.data['error']['code'] == 'validation_error'


@pytest.mark.parametrize('alias', ['admin', 'ADMIN', 'presto', 'soporte'])
def test_a_reserved_alias_returns_400(client, alias):
    """Un alias reservado devuelve 400."""
    register(client, f'alias-reservado-{uuid.uuid4().hex[:6]}@example.com')

    response = set_alias(client, alias)

    assert response.status_code == 400


def test_the_own_alias_is_returned(client):
    """El usuario puede leer su propio alias."""
    register(client, 'alias-leer@example.com')
    set_alias(client, 'nombre.leido')

    response = client.get('/api/v1/identity/alias/')

    assert response.status_code == 200
    assert response.data['alias'] == 'nombre.leido'


def test_the_alias_is_null_when_the_user_does_not_have_one(client):
    """Sin alias, el endpoint devuelve null (no 404)."""
    register(client, 'alias-sin@example.com')

    response = client.get('/api/v1/identity/alias/')

    assert response.status_code == 200
    assert response.data['alias'] is None


def test_the_alias_is_in_the_profile(client):
    """El perfil propio trae el alias."""
    register(client, 'alias-perfil@example.com')
    set_alias(client, 'nombre.perfil')

    response = client.get('/api/v1/auth/me/')

    assert response.status_code == 200
    assert response.data['alias'] == 'nombre.perfil'


def test_the_alias_is_not_exposed_in_another_user_profile(client):
    """El alias de otro usuario no se ve (los perfiles son propios)."""
    register(client, 'alias-ajeno@example.com')
    other_client = APIClient()
    register(other_client, 'alias-propio@example.com')
    set_alias(other_client, 'nombre.propio')

    response = client.get('/api/v1/auth/me/')

    assert response.status_code == 200
    assert response.data.get('alias') is None


def test_the_selector_finds_the_user_by_alias():
    """El selector de identity devuelve el usuario por su alias."""
    from apps.identity.models import User
    from apps.identity.selectors import get_user_id_by_alias

    user = User.objects.create_user(email='selector@example.com', password='TestPass123!')
    user.alias = 'alias.selector'
    user.save(update_fields=['alias'])

    assert get_user_id_by_alias('alias.selector') == user.id
    assert get_user_id_by_alias('ALIAS.SELECTOR') == user.id
    assert get_user_id_by_alias('no.existe') is None


def test_the_alias_needs_the_token(client):
    """Sin token, el endpoint responde 401."""
    response = APIClient().get('/api/v1/identity/alias/')

    assert response.status_code == 401
