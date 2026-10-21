"""Test end-to-end del flujo completo de Presto.

El test camina por la API HTTP como lo haría un cliente real: registro,
login, KYC aprobado, depósito simulado, oferta, préstamo, pago de cuota,
inversión, reportes y avisos. Al final comprueba el invariante del ledger:
**la suma de los saldos de cada moneda es cero**.

El recorrido se hace dos veces, una por moneda (ARS y USD), porque el ledger
nunca mezcla monedas.
"""

import uuid
from decimal import Decimal

import pytest
from django.db.models import Sum
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

PASSWORD = 'PrestoTest123!'


def register(client, email):
    """Registra un usuario y devuelve su id."""
    response = client.post(
        '/api/v1/auth/register/',
        {'email': email, 'password': PASSWORD},
        format='json',
    )
    assert response.status_code == 201, response.data
    return response.data['id']


def login(client, email):
    """Inicia sesión y devuelve el access token."""
    response = client.post(
        '/api/v1/auth/login/',
        {'email': email, 'password': PASSWORD},
        format='json',
    )
    assert response.status_code == 200, response.data
    return response.data['access']


def approve_kyc(user_id):
    """Aprueba el KYC del usuario.

    En producción la aprobación la hace el staff desde el admin; acá se usa el
    service, que es la única vía que usa el admin.
    """
    from apps.identity.models import User
    from apps.identity.services import resolve_kyc, submit_kyc

    user = User.objects.get(pk=user_id)
    verification = submit_kyc(user=user, documents={})
    resolve_kyc(
        verification_id=verification.id,
        status='approved',
        resolved_by_user_id=uuid.uuid4(),
    )


def create_investment_product(currency):
    """Crea un producto de plazo fijo activo en la moneda pedida.

    En producción los productos los da de alta el staff desde el admin; la API
    solo los lista.
    """
    from apps.investments.models import InvestmentProduct

    return InvestmentProduct.objects.create(
        type=InvestmentProduct.Type.FIXED_TERM,
        currency=currency,
        term_days=30,
        annual_rate_tna=Decimal('12.00'),
        min_amount=Decimal('1000.00'),
        status=InvestmentProduct.Status.ACTIVE,
    )


def total_balance(currency):
    """Devuelve la suma de los saldos de todas las cuentas de la moneda."""
    from apps.ledger.models import Account

    return Account.objects.filter(currency=currency).aggregate(total=Sum('balance'))['total']


def test_the_complete_flow_keeps_the_ledger_balanced():
    """El flujo completo, en cada moneda, deja el ledger cuadrado."""
    for currency in ('ARS', 'USD'):
        _run_the_flow(currency)


def _run_the_flow(currency):
    """Recorre el flujo completo de un usuario en la moneda indicada."""
    lender_client = APIClient()
    borrower_client = APIClient()

    # 1. Registro
    lender_id = register(lender_client, f'prestamista-{currency}@example.com')
    borrower_id = register(borrower_client, f'prestatario-{currency}@example.com')

    # 2. Login
    lender_token = login(lender_client, f'prestamista-{currency}@example.com')
    borrower_token = login(borrower_client, f'prestatario-{currency}@example.com')
    lender_client.credentials(HTTP_AUTHORIZATION=f'Bearer {lender_token}')
    borrower_client.credentials(HTTP_AUTHORIZATION=f'Bearer {borrower_token}')

    # 3. KYC aprobado (obligatorio para mover dinero)
    approve_kyc(lender_id)
    approve_kyc(borrower_id)

    # 4. Depósito simulado del prestamista
    response = lender_client.post(
        '/api/v1/ledger/transactions/',
        {
            'type': 'deposit',
            'currency': currency,
            'amount': '100000.00',
            'description': 'Depósito de prueba',
        },
        format='json',
        HTTP_IDEMPOTENCY_KEY=f'deposito-{currency}',
    )
    assert response.status_code == 201, response.data

    # 5. Oferta de préstamo
    response = lender_client.post(
        '/api/v1/offers/',
        {
            'amount': '50000.00',
            'currency': currency,
            'interest_rate': '24.00',
            'term_months': 6,
        },
        format='json',
    )
    assert response.status_code == 201, response.data
    offer_id = response.data['id']

    # 6. El prestatario acepta la oferta: el dinero se desembolsa
    response = borrower_client.post(
        '/api/v1/loans/',
        {'offer_id': offer_id},
        format='json',
        HTTP_IDEMPOTENCY_KEY=f'prestamo-{currency}',
    )
    assert response.status_code == 201, response.data
    loan_id = response.data['id']
    assert response.data['status'] == 'active'

    # El detalle del préstamo trae el snapshot de los términos y las cuotas
    response = borrower_client.get(f'/api/v1/loans/{loan_id}/')
    assert response.status_code == 200, response.data
    assert len(response.data['installments']) == 6
    assert response.data['terms_snapshot']['is_immutable'] is True

    # 7. Pago de la primera cuota
    response = borrower_client.post(f'/api/v1/loans/{loan_id}/installments/1/pay/')
    assert response.status_code == 200, response.data
    assert response.data['status'] == 'paid'

    # 8. Inversión a plazo fijo con parte del dinero recibido
    product = create_investment_product(currency)
    response = borrower_client.post(
        '/api/v1/investments/positions/',
        {
            'product_id': str(product.id),
            'amount': '10000.00',
            'currency': currency,
        },
        format='json',
        HTTP_IDEMPOTENCY_KEY=f'inversion-{currency}',
    )
    assert response.status_code == 201, response.data
    assert response.data['status'] == 'active'

    # 9. Reportes del prestatario
    for report in ('spending', 'investments', 'loans', 'movements'):
        response = borrower_client.get(f'/api/v1/reports/{report}/', {'currency': currency})
        assert response.status_code == 200, (report, response.data)

    # 10. Un presupuesto que se dispara al categorizar un gasto
    response = borrower_client.post(
        '/api/v1/budgets/categories/',
        {'name': 'Comida'},
        format='json',
    )
    assert response.status_code == 201, response.data
    category_id = response.data['id']

    response = borrower_client.post(
        '/api/v1/budgets/',
        {
            'category_id': category_id,
            'limit_amount': '1000.00',
            'currency': currency,
            'alert_threshold': 50,
        },
        format='json',
    )
    assert response.status_code == 201, response.data
    budget_id = response.data['id']

    response = borrower_client.post(
        '/api/v1/ledger/transactions/',
        {
            'type': 'withdrawal',
            'currency': currency,
            'amount': '800.00',
            'description': 'Compra del súper',
        },
        format='json',
        HTTP_IDEMPOTENCY_KEY=f'gasto-{currency}',
    )
    assert response.status_code == 201, response.data
    movement_id = response.data['id']

    response = borrower_client.post(
        '/api/v1/budgets/expenses/',
        {'category_id': category_id, 'ledger_transaction_id': movement_id},
        format='json',
    )
    assert response.status_code == 201, response.data

    response = borrower_client.get(f'/api/v1/budgets/{budget_id}/status/')
    assert response.status_code == 200, response.data
    assert response.data['alert_triggered'] is True

    # 11. Los avisos del usuario (la alerta del presupuesto)
    response = borrower_client.get('/api/v1/notifications/')
    assert response.status_code == 200, response.data
    assert response.data['count'] == 1
    assert response.data['results'][0]['event_type'] == 'budget_alert'

    # 12. El ledger quedó cuadrado: la suma de los saldos de la moneda es cero
    assert total_balance(currency) == Decimal('0.00')
