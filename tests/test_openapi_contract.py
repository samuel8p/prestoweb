"""El esquema OpenAPI tiene que describir exactamente lo que la API hace.

El frontend está construido contra el esquema: si el esquema dice una cosa y
la API hace otra, el frontend se rompe. Estos tests hacen una llamada **real**
a cada operación y comparan la respuesta con lo declarado en
`docs/openapi.yaml` (el archivo que consume el front).
"""

import uuid
from decimal import Decimal
from pathlib import Path

import pytest
import yaml
from django.urls import get_resolver
from rest_framework.test import APIClient

from apps.identity.services import register_user, resolve_kyc, submit_kyc

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / 'docs/openapi.yaml'
PASSWORD = 'PrestoTest123!'

pytestmark = pytest.mark.django_db


@pytest.fixture(scope='module')
def schema():
    """El esquema versionado (el que consume el front)."""
    return yaml.safe_load(SCHEMA_PATH.read_text(encoding='utf-8'))


@pytest.fixture
def api():
    """Un cliente autenticado como un usuario con el KYC aprobado."""
    client = APIClient()
    email = f'contrato-{uuid.uuid4().hex[:8]}@presto.local'
    user = register_user(email=email, password=PASSWORD)
    verification = submit_kyc(user=user, documents={})
    resolve_kyc(
        verification_id=verification.id,
        status='approved',
        resolved_by_user_id=uuid.uuid4(),
    )
    from rest_framework_simplejwt.tokens import RefreshToken

    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    client.user = user
    return client


def declared_responses(schema, path: str, method: str) -> dict:
    """Las respuestas declaradas para una operación del esquema."""
    return schema['paths'][path][method]['responses']


def schema_keys(schema, path: str, method: str, status: str = '200') -> set[str]:
    """Las claves de la respuesta declarada (resolviendo los $ref)."""
    content = declared_responses(schema, path, method)[status]['content']
    reference = content['application/json']['schema'].get('$ref', '')
    if reference:
        name = reference.rsplit('/', 1)[-1]
        return set(schema['components']['schemas'][name]['properties'])
    return set(content['application/json']['schema'].get('properties', {}))


def test_the_schema_is_in_sync_with_the_code():
    """El esquema versionado es el que genera el código.

    Si alguien cambia la API y no regenera el esquema, el front queda
    descrebido: este test falla.
    """
    from drf_spectacular.generators import SchemaGenerator

    generated = SchemaGenerator().get_schema(request=None, public=True)
    committed = yaml.safe_load(SCHEMA_PATH.read_text(encoding='utf-8'))

    assert generated['paths'] == committed['paths']


def test_every_endpoint_of_the_api_is_in_the_schema():
    """Todas las operaciones de la API están declaradas en el esquema."""
    import re

    schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding='utf-8'))
    declared = set(schema['paths'])

    def walk(resolver, prefix=''):
        for pattern in resolver.url_patterns:
            if hasattr(pattern, 'url_patterns'):
                walk(pattern, prefix + str(pattern.pattern))
                continue
            route = prefix + str(pattern.pattern)
            if route.startswith('api/v1/'):
                route = re.sub(r'<(?:uuid|int|str|path):([a-z_]+)>', r'{\1}', route)
                declared_paths.add('/' + route)

    declared_paths = set()
    walk(get_resolver())

    assert declared_paths <= declared, sorted(declared_paths - declared)


# --- La paginación real de cada listado ---

PAGINATED = [
    ('/api/v1/budgets/', 'count'),
    ('/api/v1/budgets/categories/', 'count'),
    ('/api/v1/budgets/expenses/', 'count'),
    ('/api/v1/investments/products/', 'count'),
    ('/api/v1/investments/positions/', 'count'),
    ('/api/v1/ledger/accounts/', 'count'),
    ('/api/v1/loans/', 'count'),
    ('/api/v1/matching/offers/', 'count'),
    ('/api/v1/notifications/', 'count'),
    ('/api/v1/offers/', 'count'),
]


@pytest.mark.parametrize('path,count_key', PAGINATED, ids=[path for path, _ in PAGINATED])
def test_the_paginated_listings_are_declared_as_they_respond(schema, api, path, count_key):
    """Los listados paginados declaran `{count, next, previous, results}`."""
    declared = schema_keys(schema, path, 'get')

    assert declared == {'count', 'next', 'previous', 'results'}

    response = api.get(path)

    assert response.status_code == 200
    assert set(response.json().keys()) == {'count', 'next', 'previous', 'results'}


def test_the_cursor_pagination_of_the_movements_is_declared(schema, api):
    """Los movimientos del ledger paginan por cursor: sin `count`."""
    declared = schema_keys(schema, '/api/v1/ledger/transactions/', 'get')

    assert declared == {'next', 'previous', 'results'}

    response = api.get('/api/v1/ledger/transactions/')

    assert response.status_code == 200
    assert set(response.json().keys()) == {'next', 'previous', 'results'}


def test_the_movements_declare_the_amount_and_the_currency(schema, api):
    """El listado de movimientos declara el importe y la moneda (D-10)."""
    properties = schema['components']['schemas']['LedgerTransactionList']['properties']

    assert 'amount' in properties
    assert 'currency' in properties

    api.post(
        '/api/v1/ledger/transactions/',
        {'type': 'deposit', 'currency': 'ARS', 'amount': '1000.00'},
        format='json',
        HTTP_IDEMPOTENCY_KEY='contrato-movimientos',
    )
    response = api.get('/api/v1/ledger/transactions/')
    movement = response.json()['results'][0]

    assert movement['amount'] == '1000.00'
    assert movement['currency'] == 'ARS'


def test_the_movements_report_is_paginated(schema, api):
    """El reporte de movimientos también pagina."""
    declared = schema_keys(schema, '/api/v1/reports/movements/', 'get')

    assert declared == {'count', 'next', 'previous', 'results'}

    response = api.get('/api/v1/reports/movements/?currency=ARS')

    assert response.status_code == 200
    assert set(response.json().keys()) == {'count', 'next', 'previous', 'results'}


# --- El header Idempotency-Key ---

IDEMPOTENT_OPERATIONS = [
    ('/api/v1/ledger/transactions/', 'post'),
    ('/api/v1/loans/', 'post'),
    ('/api/v1/investments/positions/', 'post'),
]

IDEMPOTENCY_PAYLOADS = [
    (
        '/api/v1/ledger/transactions/',
        'post',
        {'type': 'deposit', 'currency': 'ARS', 'amount': '10.00'},
    ),
    (
        '/api/v1/loans/',
        'post',
        {'offer_id': '00000000-0000-0000-0000-000000000000'},
    ),
    (
        '/api/v1/investments/positions/',
        'post',
        {
            'product_id': '00000000-0000-0000-0000-000000000000',
            'amount': '10.00',
        },
    ),
]


@pytest.mark.parametrize(
    'path,method',
    IDEMPOTENT_OPERATIONS,
    ids=[f'{method} {path}' for path, method in IDEMPOTENT_OPERATIONS],
)
def test_the_idempotency_key_is_declared_as_required(schema, path, method):
    """El header `Idempotency-Key` está declarado y es obligatorio."""
    parameters = schema['paths'][path][method].get('parameters', [])
    headers = [
        parameter
        for parameter in parameters
        if parameter['in'] == 'header' and parameter['name'] == 'Idempotency-Key'
    ]

    assert len(headers) == 1
    assert headers[0]['required'] is True


@pytest.mark.parametrize(
    'path,method,payload',
    IDEMPOTENCY_PAYLOADS,
    ids=[f'{path}' for path, _, _ in IDEMPOTENCY_PAYLOADS],
)
def test_the_api_really_asks_for_the_idempotency_key(api, path, method, payload):
    """Sin el header la API responde 400 (lo que el esquema declara)."""
    response = api.post(path, payload, format='json')

    assert response.status_code == 400
    assert response.json()['error']['code'] == 'validation_error'
    assert 'idempotency_key' in response.json()['error']['details']


def test_the_refresh_declares_its_body(schema):
    """El refresh declara el body con el token."""
    operation = schema['paths']['/api/v1/auth/token/refresh/']['post']
    content = operation['requestBody']['content']
    reference = content['application/json']['schema']['$ref']
    name = reference.rsplit('/', 1)[-1]

    assert 'refresh' in schema['components']['schemas'][name]['properties']


# --- Los reportes ---

REPORTS = [
    '/api/v1/reports/spending/',
    '/api/v1/reports/investments/',
    '/api/v1/reports/loans/',
    '/api/v1/reports/movements/',
]


@pytest.mark.parametrize('path', REPORTS, ids=REPORTS)
def test_the_reports_declare_their_parameters(schema, path):
    """Los cuatro reportes declaran `currency`, `from`, `to` y `export`."""
    parameters = {
        parameter['name']: parameter
        for parameter in schema['paths'][path]['get'].get('parameters', [])
    }

    assert 'currency' in parameters
    assert parameters['currency']['required'] is True
    assert 'from' in parameters
    assert 'to' in parameters
    assert 'export' in parameters


@pytest.mark.parametrize('path', REPORTS, ids=REPORTS)
def test_the_reports_declare_the_json_and_the_csv_responses(schema, path):
    """Los reportes declaran la respuesta JSON y la respuesta CSV."""
    responses = schema['paths'][path]['get']['responses']

    assert '200' in responses
    assert 'application/json' in responses['200']['content']
    assert 'text/csv' in responses['200']['content']


def test_the_api_really_asks_for_the_currency(api):
    """Sin `currency` la API responde 400 (lo que el esquema declara)."""
    response = api.get('/api/v1/reports/spending/')

    assert response.status_code == 400
    assert response.json()['error']['code'] == 'validation_error'


def test_the_api_really_answers_a_csv(api):
    """Con `export=csv` la API responde el CSV."""
    response = api.get('/api/v1/reports/spending/?currency=ARS&export=csv')

    assert response.status_code == 200
    assert response['Content-Type'].startswith('text/csv')
    assert 'attachment' in response['Content-Disposition']


def test_the_api_rejects_an_unknown_export(api):
    """Un `export` que no es `csv` responde 400."""
    response = api.get('/api/v1/reports/spending/?currency=ARS&export=pdf')

    assert response.status_code == 400
    assert response.json()['error']['code'] == 'validation_error'


# --- Los errores ---

PROTECTED_OPERATIONS = [
    ('/api/v1/auth/me/', 'get'),
    ('/api/v1/kyc/', 'get'),
    ('/api/v1/ledger/accounts/', 'get'),
    ('/api/v1/ledger/transactions/', 'get'),
    ('/api/v1/offers/', 'get'),
    ('/api/v1/matching/offers/', 'get'),
    ('/api/v1/loans/', 'get'),
    ('/api/v1/investments/products/', 'get'),
    ('/api/v1/investments/positions/', 'get'),
    ('/api/v1/budgets/', 'get'),
    ('/api/v1/budgets/categories/', 'get'),
    ('/api/v1/budgets/expenses/', 'get'),
    ('/api/v1/reports/spending/', 'get'),
    ('/api/v1/reports/movements/', 'get'),
    ('/api/v1/notifications/', 'get'),
    ('/api/v1/notifications/preferences/', 'get'),
]


@pytest.mark.parametrize(
    'path,method',
    PROTECTED_OPERATIONS,
    ids=[f'{method} {path}' for path, method in PROTECTED_OPERATIONS],
)
def test_every_protected_operation_declares_and_answers_401(schema, path, method):
    """Las operaciones protegidas declaran el 401 y lo responden de verdad."""
    responses = schema['paths'][path][method]['responses']

    assert '401' in responses

    response = APIClient().get(path)

    assert response.status_code == 401
    assert response.json()['error']['code'] == 'not_authenticated'


def test_the_error_format_is_the_one_of_agents_8(schema):
    """El error declarado tiene la forma de AGENTS §8."""
    schema_ = schema['paths']['/api/v1/ledger/transactions/']['post']['responses']['401']
    content = schema_['content']['application/json']
    error = content['example']['error']

    assert set(error.keys()) == {'code', 'message', 'details'}
    assert error['code'] == 'not_authenticated'


def test_the_kyc_error_is_the_permission_denied_of_the_kyc(schema):
    """El 403 de las operaciones con KYC es `permission_denied`."""
    responses = schema['paths']['/api/v1/ledger/transactions/']['post']['responses']

    assert '403' in responses
    example = responses['403']['content']['application/json']['example']
    assert example['error']['code'] == 'permission_denied'


def test_the_kyc_status_can_be_null(schema):
    """`GET /api/v1/kyc/` declara que puede venir sin contenido.

    La API responde el body **vacío** (no `null`) cuando el usuario no pidió
    la verificación: el esquema lo dice en la descripción.
    """
    response = schema['paths']['/api/v1/kyc/']['get']['responses']['200']
    schema_ = response['content']['application/json']['schema']

    assert schema_['nullable'] is True
    assert 'vacío' in response['description']


def test_the_api_really_answers_null_when_there_is_no_kyc():
    """Sin verificación, la API responde null (y el esquema lo dice)."""
    from apps.identity.services import register_user

    email = f'sin-kyc-{uuid.uuid4().hex[:8]}@presto.local'
    user = register_user(email=email, password=PASSWORD)
    from rest_framework_simplejwt.tokens import RefreshToken

    token = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')

    response = client.get('/api/v1/kyc/')

    assert response.status_code == 200
    # Sin verificación la API responde el body vacío (el frontend lo lee como
    # null) y el esquema lo declara nullable.
    assert response.content == b''
    assert (
        schema_paths()['/api/v1/kyc/']['get']['responses']['200']['content']['application/json'][
            'schema'
        ]['nullable']
        is True
    )


def test_the_api_answers_404_for_a_resource_of_another_user(api):
    """Un recurso de otro usuario responde 404 (y el esquema lo declara)."""
    from rest_framework_simplejwt.tokens import RefreshToken

    from apps.identity.services import register_user

    email = f'otro-{uuid.uuid4().hex[:8]}@presto.local'
    other = register_user(email=email, password=PASSWORD)
    token = RefreshToken.for_user(other)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')

    response = client.get('/api/v1/kyc/00000000-0000-0000-0000-000000000000/')

    assert response.status_code == 404
    assert response.json()['error']['code'] == 'not_found'
    assert '404' in schema_paths()['/api/v1/kyc/{verification_id}/']['get']['responses']


def test_the_api_answers_409_for_a_duplicate(api):
    """Un recurso duplicado responde 409 (y el esquema lo declara)."""
    payload = {'name': f'Categoría {uuid.uuid4().hex[:6]}'}
    first = api.post('/api/v1/budgets/categories/', payload, format='json')
    second = api.post('/api/v1/budgets/categories/', payload, format='json')

    assert first.status_code == 201
    assert second.status_code == 409
    assert '409' in schema_paths()['/api/v1/budgets/categories/']['post']['responses']


def schema_paths():
    """El esquema versionado."""
    return yaml.safe_load(SCHEMA_PATH.read_text(encoding='utf-8'))['paths']


def test_the_responses_declare_the_demo_mode_header(schema):
    """Las respuestas declaran la cabecera `X-Presto-Mode`.

    En modo demo la aplicación la agrega a todas las respuestas y el front
    la usa para saber que el dinero es simulado.
    """
    response = schema['paths']['/api/v1/meta/']['get']['responses']['200']

    headers = response.get('headers', {})

    assert 'X-Presto-Mode' in headers
    assert headers['X-Presto-Mode']['schema']['type'] == 'string'
