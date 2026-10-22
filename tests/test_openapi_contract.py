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


def test_the_movements_report_is_paginated(schema, api):
    """El reporte de movimientos también pagina."""
    declared = schema_keys(schema, '/api/v1/reports/movements/', 'get')

    assert declared == {'count', 'next', 'previous', 'results'}

    response = api.get('/api/v1/reports/movements/?currency=ARS')

    assert response.status_code == 200
    assert set(response.json().keys()) == {'count', 'next', 'previous', 'results'}
