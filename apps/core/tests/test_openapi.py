"""Tests del esquema OpenAPI de la API.

El esquema tiene que generarse sin errores ni warnings: la CI corre
``manage.py spectacular --validate --fail-on-warn`` y ese comando falla si
queda algún warning.
"""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from drf_spectacular.drainage import reset_generator_stats
from drf_spectacular.generators import SchemaGenerator


def generate_schema() -> dict:
    """Devuelve el esquema OpenAPI generado a partir del URLConf del proyecto."""
    return SchemaGenerator().get_schema(request=None, public=True)


def list_operation_ids(schema: dict) -> list[str]:
    """Devuelve los operationId de todas las operaciones del esquema."""
    return [
        operation['operationId']
        for path_item in schema['paths'].values()
        for operation in path_item.values()
        if isinstance(operation, dict) and 'operationId' in operation
    ]


def test_openapi_schema_is_generated_without_errors_or_warnings():
    """`spectacular --validate --fail-on-warn` no debe fallar (es lo que corre la CI)."""
    reset_generator_stats()
    try:
        call_command('spectacular', '--validate', '--fail-on-warn', stdout=StringIO())
    except CommandError as exc:
        pytest.fail(f'El esquema OpenAPI se generó con errores o warnings: {exc}')


def test_openapi_schema_documents_the_installment_payment_endpoint():
    """El pago de cuotas está documentado y no declara un body que la vista ignora."""
    path_item = generate_schema()['paths']['/api/v1/loans/{loan_id}/installments/{number}/pay/']

    assert 'post' in path_item
    assert 'requestBody' not in path_item['post']


def test_openapi_operation_ids_are_unique():
    """Ningún operationId se repite: las listas y los detalles se distinguen."""
    operation_ids = list_operation_ids(generate_schema())

    assert operation_ids
    assert len(operation_ids) == len(set(operation_ids))


def test_openapi_list_and_detail_operations_have_distinct_ids():
    """Cada lista y su detalle tienen operationId propio y explícito."""
    operation_ids = list_operation_ids(generate_schema())

    for list_id, detail_id in (
        ('kyc_list', 'kyc_retrieve'),
        ('ledger_transactions_list', 'ledger_transactions_retrieve'),
        ('loans_list', 'loans_retrieve'),
        ('offers_list', 'offers_retrieve'),
        ('investments_positions_list', 'investments_positions_retrieve'),
    ):
        assert list_id in operation_ids
        assert detail_id in operation_ids


def test_openapi_status_enums_have_explicit_names():
    """Los choice sets de `status` que colisionaban tienen nombre propio."""
    schemas = generate_schema()['components']['schemas']

    assert 'LoanStatusEnum' in schemas
    assert 'PositionStatusEnum' in schemas
