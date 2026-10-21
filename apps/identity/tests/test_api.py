"""Tests de la API de identity."""

import pytest
from rest_framework.test import APIClient

from apps.identity.tests.factories import KYCVerificationFactory, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def authenticate(client, user):
    """Autentica al cliente con un access token del usuario dado."""
    from rest_framework_simplejwt.tokens import RefreshToken

    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


def test_register_returns_201_and_creates_user(client):
    """El registro devuelve 201 y crea el usuario con su perfil."""
    from apps.identity.models import User

    response = client.post(
        '/api/v1/auth/register/',
        {'email': 'nuevo@example.com', 'password': 'TestPass123!'},
        format='json',
    )

    assert response.status_code == 201
    assert response.data['email'] == 'nuevo@example.com'
    assert User.objects.filter(email='nuevo@example.com').exists()


def test_register_does_not_expose_password(client):
    """La respuesta del registro nunca incluye la contraseña."""
    response = client.post(
        '/api/v1/auth/register/',
        {'email': 'nuevo@example.com', 'password': 'TestPass123!'},
        format='json',
    )

    assert 'password' not in response.data
    assert 'TestPass123!' not in str(response.data)


def test_register_rejects_duplicate_email(client):
    """El email duplicado devuelve 400 con el formato de AGENTS §8."""
    UserFactory(email='duplicado@example.com')

    response = client.post(
        '/api/v1/auth/register/',
        {'email': 'duplicado@example.com', 'password': 'TestPass123!'},
        format='json',
    )

    assert response.status_code == 400
    assert response.data['error']['code'] == 'validation_error'
    assert 'error' in response.data


def test_register_rejects_invalid_email(client):
    """Un email inválido devuelve 400."""
    response = client.post(
        '/api/v1/auth/register/',
        {'email': 'no-es-un-email', 'password': 'TestPass123!'},
        format='json',
    )

    assert response.status_code == 400


def test_register_rejects_short_password(client):
    """Una contraseña corta devuelve 400."""
    response = client.post(
        '/api/v1/auth/register/',
        {'email': 'corto@example.com', 'password': '123'},
        format='json',
    )

    assert response.status_code == 400


def test_login_returns_access_and_refresh_tokens(client):
    """El login devuelve access y refresh tokens."""
    user = UserFactory(email='login@example.com', password='TestPass123!')

    response = client.post(
        '/api/v1/auth/login/',
        {'email': 'login@example.com', 'password': 'TestPass123!'},
        format='json',
    )

    assert response.status_code == 200
    assert response.data['access']
    assert response.data['refresh']
    assert response.data['user']['email'] == user.email


def test_login_rejects_wrong_password(client):
    """Una contraseña incorrecta devuelve 401."""
    UserFactory(email='login@example.com', password='TestPass123!')

    response = client.post(
        '/api/v1/auth/login/',
        {'email': 'login@example.com', 'password': 'Incorrecta123!'},
        format='json',
    )

    assert response.status_code == 401
    assert response.data['error']['code'] == 'not_authenticated'


def test_login_rejects_unknown_email(client):
    """Un email inexistente devuelve 401."""
    response = client.post(
        '/api/v1/auth/login/',
        {'email': 'nadie@example.com', 'password': 'TestPass123!'},
        format='json',
    )

    assert response.status_code == 401


def test_login_is_throttled_after_five_attempts(client):
    """El login se limita a 5 intentos por minuto (AGENTS §9.6)."""
    UserFactory(email='login@example.com', password='TestPass123!')
    payload = {'email': 'login@example.com', 'password': 'Incorrecta123!'}

    for _ in range(5):
        client.post('/api/v1/auth/login/', payload, format='json')

    response = client.post('/api/v1/auth/login/', payload, format='json')

    assert response.status_code == 429
    assert response.data['error']['code'] == 'throttled'


def test_register_is_throttled_after_five_attempts(client):
    """El registro se limita a 5 intentos por hora (AGENTS §9.6)."""
    statuses = []
    for index in range(6):
        response = client.post(
            '/api/v1/auth/register/',
            {'email': f'throttle{index}@example.com', 'password': 'TestPass123!'},
            format='json',
        )
        statuses.append(response.status_code)

    assert statuses[:5] == [201] * 5
    assert statuses[5] == 429


def test_refresh_rotates_and_blacklists_token(client):
    """El refresh rota el token y el anterior queda blacklisted."""
    user = UserFactory(email='refresh@example.com', password='TestPass123!')

    login_response = client.post(
        '/api/v1/auth/login/',
        {'email': user.email, 'password': 'TestPass123!'},
        format='json',
    )
    first_refresh = login_response.data['refresh']

    refresh_response = client.post(
        '/api/v1/auth/token/refresh/',
        {'refresh': first_refresh},
        format='json',
    )

    assert refresh_response.status_code == 200
    assert refresh_response.data['access']
    assert refresh_response.data['refresh'] != first_refresh

    reused_response = client.post(
        '/api/v1/auth/token/refresh/',
        {'refresh': first_refresh},
        format='json',
    )

    assert reused_response.status_code == 401


def test_me_requires_authentication(client):
    """El perfil propio exige autenticación."""
    response = client.get('/api/v1/auth/me/')

    assert response.status_code == 401
    assert response.data['error']['code'] == 'not_authenticated'


def test_me_returns_own_user(client):
    """El perfil propio devuelve los datos del usuario autenticado."""
    user = UserFactory(email='mio@example.com')
    authenticate(client, user)

    response = client.get('/api/v1/auth/me/')

    assert response.status_code == 200
    assert response.data['email'] == 'mio@example.com'
    assert response.data['id'] == str(user.id)


def test_me_patch_updates_profile(client):
    """El perfil propio se actualiza con PATCH."""
    user = UserFactory(email='mio@example.com')
    authenticate(client, user)

    response = client.patch(
        '/api/v1/auth/me/',
        {'phone_number': '+5491100000000', 'country': 'AR'},
        format='json',
    )

    assert response.status_code == 200
    assert response.data['profile']['phone_number'] == '+5491100000000'
    assert response.data['profile']['country'] == 'AR'


def test_me_patch_does_not_touch_other_user_profile(client):
    """Un usuario no puede modificar el perfil de otro."""
    other = UserFactory(email='otro@example.com')
    user = UserFactory(email='mio@example.com')
    authenticate(client, user)

    response = client.patch(
        '/api/v1/auth/me/',
        {'phone_number': '+5491199999999', 'country': 'AR'},
        format='json',
    )

    assert response.status_code == 200
    from apps.identity.selectors import get_profile

    assert (
        get_profile(user_id=other.id) is None
        or get_profile(user_id=other.id).phone_number != '+5491199999999'
    )


def test_kyc_get_returns_own_status(client):
    """El endpoint de KYC devuelve el estado de verificación del propio usuario."""
    user = UserFactory()
    verification = KYCVerificationFactory(user=user, status='approved')
    authenticate(client, user)

    response = client.get('/api/v1/kyc/')

    assert response.status_code == 200
    assert response.data['status'] == 'approved'
    assert response.data['id'] == str(verification.id)


def test_kyc_get_returns_none_without_verifications(client):
    """Sin verificaciones el endpoint responde null."""
    user = UserFactory()
    authenticate(client, user)

    response = client.get('/api/v1/kyc/')

    assert response.status_code == 200
    assert response.data is None


def test_kyc_post_creates_pending_verification(client):
    """Enviar documentos crea una verificación pending."""
    user = UserFactory()
    authenticate(client, user)

    response = client.post(
        '/api/v1/kyc/',
        {'documents': {'front': 'passport.jpg'}},
        format='json',
    )

    assert response.status_code == 201
    assert response.data['status'] == 'pending'


def test_kyc_post_rejects_second_pending_verification(client):
    """Un usuario con verificación pendiente no puede volver a enviar."""
    user = UserFactory()
    KYCVerificationFactory(user=user, status='pending')
    authenticate(client, user)

    response = client.post(
        '/api/v1/kyc/',
        {'documents': {}},
        format='json',
    )

    assert response.status_code == 400
    assert response.data['error']['code'] == 'validation_error'


def test_kyc_detail_of_other_user_returns_404(client):
    """Un usuario no puede ver la verificación de otro (AGENTS §9.1)."""
    other = UserFactory()
    verification = KYCVerificationFactory(user=other, status='approved')
    user = UserFactory()
    authenticate(client, user)

    response = client.get(f'/api/v1/kyc/{verification.id}/')

    assert response.status_code == 404
    assert response.data['error']['code'] == 'not_found'


def test_kyc_detail_of_own_verification_returns_200(client):
    """El usuario ve su propia verificación por detalle."""
    user = UserFactory()
    verification = KYCVerificationFactory(user=user, status='approved')
    authenticate(client, user)

    response = client.get(f'/api/v1/kyc/{verification.id}/')

    assert response.status_code == 200
    assert response.data['id'] == str(verification.id)


def test_kyc_post_does_not_create_verification_for_other_user(client):
    """La verificación enviada siempre pertenece al usuario autenticado."""
    other = UserFactory()
    user = UserFactory()
    authenticate(client, user)

    response = client.post(
        '/api/v1/kyc/',
        {'documents': {}},
        format='json',
    )

    assert response.status_code == 201
    from apps.identity.models import KYCVerification

    assert KYCVerification.objects.filter(user=user).count() == 1
    assert KYCVerification.objects.filter(user=other).count() == 0


def test_openapi_schema_is_served(client):
    """El esquema OpenAPI se publica en /api/schema/."""
    response = client.get('/api/schema/')

    assert response.status_code == 200
    assert response['Content-Type'].startswith('application/vnd.oai.openapi')


def test_openapi_schema_documents_identity_endpoints(client):
    """El esquema documenta los endpoints de identity."""
    response = client.get('/api/schema/')
    schema = response.data

    assert '/api/v1/auth/register/' in schema['paths']
    assert '/api/v1/auth/login/' in schema['paths']
    assert '/api/v1/auth/token/refresh/' in schema['paths']
    assert '/api/v1/auth/me/' in schema['paths']
    assert '/api/v1/kyc/' in schema['paths']


def test_swagger_docs_are_served(client):
    """La documentación Swagger se publica en /api/docs/."""
    response = client.get('/api/docs/')

    assert response.status_code == 200


def test_get_user_email_returns_the_email():
    """El selector devuelve el email del usuario."""
    from apps.identity.selectors import get_user_email

    user = UserFactory(email='selector-email@example.com')

    assert get_user_email(user_id=user.id) == 'selector-email@example.com'


def test_get_user_email_returns_none_for_an_unknown_user():
    """Un usuario que no existe no tiene email."""
    import uuid

    from apps.identity.selectors import get_user_email

    assert get_user_email(user_id=uuid.uuid4()) is None
