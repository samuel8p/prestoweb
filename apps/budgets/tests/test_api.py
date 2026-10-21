"""Tests de la API de budgets."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.budgets.tests.factories import create_approved_user

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


def fund_user(user_id, amount='10000.00', currency='ARS', key='fund'):
    """Deposita fondos simulados en la billetera del usuario."""
    from apps.ledger.services import deposit

    return deposit(
        user_id=user_id,
        currency=currency,
        amount=Decimal(amount),
        idempotency_key=key,
    )


def make_withdrawal(user_id, amount='100.00', key='gasto'):
    """Retira fondos de la billetera del usuario."""
    from apps.ledger.services import withdraw

    return withdraw(
        user_id=user_id,
        currency='ARS',
        amount=Decimal(amount),
        idempotency_key=key,
    )


def test_budgets_endpoints_require_authentication(client):
    """Todos los endpoints de budgets exigen autenticación."""
    for url in (
        '/api/v1/budgets/',
        '/api/v1/budgets/categories/',
        '/api/v1/budgets/expenses/',
    ):
        response = client.get(url)

        assert response.status_code == 401
        assert response.data['error']['code'] == 'not_authenticated'


def test_create_category_returns_201(client):
    """Crear una categoría devuelve 201 con la categoría."""
    user = create_approved_user(email='api-categoria@example.com')
    authenticate(client, user)

    response = client.post('/api/v1/budgets/categories/', {'name': 'Comida'}, format='json')

    assert response.status_code == 201
    assert response.data['name'] == 'Comida'


def test_create_category_with_an_empty_name_returns_400(client):
    """Una categoría sin nombre devuelve 400."""
    user = create_approved_user(email='api-categoria-vacia@example.com')
    authenticate(client, user)

    response = client.post('/api/v1/budgets/categories/', {'name': '  '}, format='json')

    assert response.status_code == 400


def test_create_category_with_a_duplicate_name_returns_409(client):
    """Repetir el nombre de una categoría devuelve 409."""
    user = create_approved_user(email='api-categoria-dup@example.com')
    authenticate(client, user)
    client.post('/api/v1/budgets/categories/', {'name': 'Comida'}, format='json')

    response = client.post('/api/v1/budgets/categories/', {'name': 'Comida'}, format='json')

    assert response.status_code == 409


def test_categories_list_returns_only_own_categories(client):
    """El listado de categorías solo devuelve las del usuario."""
    user = create_approved_user(email='api-categorias-lista@example.com')
    other = create_approved_user(email='api-categorias-ajeno@example.com')
    authenticate(client, other)
    client.post('/api/v1/budgets/categories/', {'name': 'Ajena'}, format='json')
    client.credentials()
    authenticate(client, user)
    client.post('/api/v1/budgets/categories/', {'name': 'Comida'}, format='json')

    response = client.get('/api/v1/budgets/categories/')

    assert response.status_code == 200
    assert [category['name'] for category in response.data['results']] == ['Comida']


def test_create_budget_returns_201(client):
    """Crear un presupuesto devuelve 201."""
    user = create_approved_user(email='api-presupuesto@example.com')
    authenticate(client, user)
    category = client.post(
        '/api/v1/budgets/categories/',
        {'name': 'Comida'},
        format='json',
    ).data

    response = client.post(
        '/api/v1/budgets/',
        {
            'category_id': category['id'],
            'limit_amount': '50000.00',
            'currency': 'ARS',
            'alert_threshold': 80,
        },
        format='json',
    )

    assert response.status_code == 201
    assert response.data['limit_amount'] == '50000.00'
    assert response.data['currency'] == 'ARS'
    assert response.data['period'] == 'monthly'


def test_create_budget_with_another_users_category_returns_404(client):
    """No se puede crear un presupuesto sobre una categoría ajena."""
    user = create_approved_user(email='api-presupuesto-ajeno@example.com')
    other = create_approved_user(email='api-presupuesto-otro@example.com')
    authenticate(client, other)
    category = client.post(
        '/api/v1/budgets/categories/',
        {'name': 'Comida'},
        format='json',
    ).data
    client.credentials()
    authenticate(client, user)

    response = client.post(
        '/api/v1/budgets/',
        {
            'category_id': category['id'],
            'limit_amount': '50000.00',
            'currency': 'ARS',
            'alert_threshold': 80,
        },
        format='json',
    )

    assert response.status_code == 404


def test_budget_detail_of_another_user_returns_404(client):
    """Un presupuesto ajeno no se expone."""
    user = create_approved_user(email='api-presupuesto-404@example.com')
    other = create_approved_user(email='api-presupuesto-404-otro@example.com')
    authenticate(client, other)
    category = client.post(
        '/api/v1/budgets/categories/',
        {'name': 'Comida'},
        format='json',
    ).data
    budget = client.post(
        '/api/v1/budgets/',
        {
            'category_id': category['id'],
            'limit_amount': '50000.00',
            'currency': 'ARS',
            'alert_threshold': 80,
        },
        format='json',
    ).data
    client.credentials()
    authenticate(client, user)

    response = client.get(f'/api/v1/budgets/{budget["id"]}/')

    assert response.status_code == 404


def test_budget_status_reports_the_spent_amount(client):
    """El estado del presupuesto informa el gastado y el límite."""
    user = create_approved_user(email='api-estado@example.com')
    authenticate(client, user)
    category = client.post(
        '/api/v1/budgets/categories/',
        {'name': 'Comida'},
        format='json',
    ).data
    budget = client.post(
        '/api/v1/budgets/',
        {
            'category_id': category['id'],
            'limit_amount': '1000.00',
            'currency': 'ARS',
            'alert_threshold': 80,
        },
        format='json',
    ).data
    fund_user(user.id, key='api-estado')
    movement = make_withdrawal(user.id, amount='250.00', key='api-estado-gasto')
    client.post(
        '/api/v1/budgets/expenses/',
        {
            'category_id': category['id'],
            'ledger_transaction_id': str(movement.id),
        },
        format='json',
    )

    response = client.get(f'/api/v1/budgets/{budget["id"]}/status/')

    assert response.status_code == 200
    assert response.data['spent_amount'] == '250.00'
    assert response.data['limit_amount'] == '1000.00'
    assert response.data['alert_triggered'] is False


def test_categorize_movement_returns_201(client):
    """Categorizar un movimiento devuelve 201."""
    user = create_approved_user(email='api-gasto@example.com')
    authenticate(client, user)
    category = client.post(
        '/api/v1/budgets/categories/',
        {'name': 'Comida'},
        format='json',
    ).data
    fund_user(user.id, key='api-gasto')
    movement = make_withdrawal(user.id, amount='100.00', key='api-gasto-retiro')

    response = client.post(
        '/api/v1/budgets/expenses/',
        {
            'category_id': category['id'],
            'ledger_transaction_id': str(movement.id),
        },
        format='json',
    )

    assert response.status_code == 201
    assert response.data['ledger_transaction_id'] == str(movement.id)
    assert response.data['category']['name'] == 'Comida'


def test_categorize_movement_twice_returns_409(client):
    """Categorizar dos veces el mismo movimiento devuelve 409."""
    user = create_approved_user(email='api-gasto-dup@example.com')
    authenticate(client, user)
    category = client.post(
        '/api/v1/budgets/categories/',
        {'name': 'Comida'},
        format='json',
    ).data
    fund_user(user.id, key='api-gasto-dup')
    movement = make_withdrawal(user.id, amount='100.00', key='api-gasto-dup-retiro')
    payload = {
        'category_id': category['id'],
        'ledger_transaction_id': str(movement.id),
    }
    client.post('/api/v1/budgets/expenses/', payload, format='json')

    response = client.post('/api/v1/budgets/expenses/', payload, format='json')

    assert response.status_code == 409


def test_categorize_a_deposit_returns_400(client):
    """Un depósito no es un gasto: devuelve 400."""
    user = create_approved_user(email='api-gasto-deposito@example.com')
    authenticate(client, user)
    category = client.post(
        '/api/v1/budgets/categories/',
        {'name': 'Comida'},
        format='json',
    ).data
    movement = fund_user(user.id, key='api-gasto-deposito')

    response = client.post(
        '/api/v1/budgets/expenses/',
        {
            'category_id': category['id'],
            'ledger_transaction_id': str(movement.id),
        },
        format='json',
    )

    assert response.status_code == 400


def test_categorize_a_movement_of_another_user_returns_404(client):
    """Un movimiento ajeno no se puede categorizar: devuelve 404."""
    user = create_approved_user(email='api-gasto-ajeno@example.com')
    other = create_approved_user(email='api-gasto-ajeno-otro@example.com')
    authenticate(client, user)
    category = client.post(
        '/api/v1/budgets/categories/',
        {'name': 'Comida'},
        format='json',
    ).data
    fund_user(other.id, key='api-gasto-ajeno')
    movement = make_withdrawal(other.id, amount='100.00', key='api-gasto-ajeno-retiro')

    response = client.post(
        '/api/v1/budgets/expenses/',
        {
            'category_id': category['id'],
            'ledger_transaction_id': str(movement.id),
        },
        format='json',
    )

    assert response.status_code == 404


def test_expenses_list_returns_only_own_expenses(client):
    """El listado de gastos solo devuelve los del usuario."""
    user = create_approved_user(email='api-gastos-lista@example.com')
    authenticate(client, user)
    category = client.post(
        '/api/v1/budgets/categories/',
        {'name': 'Comida'},
        format='json',
    ).data
    fund_user(user.id, key='api-gastos-lista')
    movement = make_withdrawal(user.id, amount='100.00', key='api-gastos-lista-retiro')
    client.post(
        '/api/v1/budgets/expenses/',
        {
            'category_id': category['id'],
            'ledger_transaction_id': str(movement.id),
        },
        format='json',
    )

    response = client.get('/api/v1/budgets/expenses/')

    assert response.status_code == 200
    assert len(response.data['results']) == 1
    assert response.data['results'][0]['ledger_transaction_id'] == str(movement.id)


def test_budget_status_accepts_an_explicit_period(client):
    """El estado del presupuesto acepta el período por query string."""
    user = create_approved_user(email='api-estado-periodo@example.com')
    authenticate(client, user)
    category = client.post(
        '/api/v1/budgets/categories/',
        {'name': 'Comida'},
        format='json',
    ).data
    budget = client.post(
        '/api/v1/budgets/',
        {
            'category_id': category['id'],
            'limit_amount': '1000.00',
            'currency': 'ARS',
            'alert_threshold': 80,
        },
        format='json',
    ).data
    now = datetime.now(UTC)

    response = client.get(
        f'/api/v1/budgets/{budget["id"]}/status/?year={now.year}&month={now.month}'
    )

    assert response.status_code == 200
    assert response.data['year'] == now.year
    assert response.data['month'] == now.month
