"""Tests de la API de reports: préstamos."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.reports.tests.test_api import create_user, fund_user

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


def create_loan(lender, borrower, amount='3000.00', months=3, key='prestamo', currency='ARS'):
    """Crea un préstamo aceptado entre el prestamista y el prestatario."""
    from apps.loans.services import accept_offer
    from apps.offers.services import create_offer

    offer = create_offer(
        lender_user_id=lender.id,
        amount=Decimal(amount),
        currency=currency,
        interest_rate=Decimal('24.00'),
        term_months=months,
    )
    return accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key=f'accept-{key}',
    )


def pay_installment(loan, borrower, number=1, key='pago'):
    """Paga una cuota del préstamo."""
    from apps.ledger.services import deposit
    from apps.loans.services import pay_installment as service_pay

    deposit(
        user_id=borrower.id,
        currency='ARS',
        amount=Decimal('10000.00'),
        idempotency_key=f'fund-{key}',
    )
    return service_pay(
        loan_id=loan.id,
        number=number,
        borrower_user_id=borrower.id,
    )


def test_loans_report_requires_authentication(client):
    """Sin token el reporte responde 401."""
    response = client.get('/api/v1/reports/loans/?currency=ARS')

    assert response.status_code == 401


def test_loans_report_requires_the_currency(client):
    """La moneda es obligatoria."""
    user = create_user(email='prestamos-sin-moneda@example.com')
    authenticate(client, user)

    response = client.get('/api/v1/reports/loans/')

    assert response.status_code == 400


def test_loans_report_summarizes_the_loans_as_borrower_and_lender(client):
    """El reporte separa lo que el usuario debe de lo que le deben."""
    lender = create_user(email='prestamos-prestamista@example.com')
    borrower = create_user(email='prestamos-prestatario@example.com')
    authenticate(client, borrower)
    fund_user(lender.id, key='prestamos-1')
    loan = create_loan(lender, borrower, key='prestamos-1')
    pay_installment(loan, borrower, number=1, key='prestamos-1')

    response = client.get('/api/v1/reports/loans/?currency=ARS')

    assert response.status_code == 200
    assert response.data['currency'] == 'ARS'
    as_borrower = response.data['as_borrower']
    assert as_borrower['active_loans'] == 1
    assert as_borrower['outstanding_amount'] == '2080.52'
    assert as_borrower['interest_amount'] == '60.00'
    assert len(as_borrower['next_installments']) == 1
    next_installment = as_borrower['next_installments'][0]
    assert next_installment['loan_id'] == str(loan.id)
    assert next_installment['number'] == 2
    assert next_installment['amount'] == '1040.26'
    as_lender = response.data['as_lender']
    assert as_lender['active_loans'] == 0
    assert as_lender['outstanding_amount'] == '0.00'
    assert as_lender['interest_amount'] == '0.00'


def test_loans_report_shows_the_interest_collected_by_the_lender(client):
    """El prestamista ve el interés cobrado."""
    lender = create_user(email='prestamos-cobrador@example.com')
    borrower = create_user(email='prestamos-deudor@example.com')
    authenticate(client, lender)
    fund_user(lender.id, key='prestamos-2')
    loan = create_loan(lender, borrower, key='prestamos-2')
    pay_installment(loan, borrower, number=1, key='prestamos-2')

    response = client.get('/api/v1/reports/loans/?currency=ARS')

    assert response.data['as_lender']['interest_amount'] == '60.00'
    assert response.data['as_lender']['outstanding_amount'] == '2080.52'
    assert response.data['as_borrower']['active_loans'] == 0


def test_loans_report_separates_currencies(client):
    """Un préstamo en USD no aparece en el reporte de ARS."""
    lender = create_user(email='prestamos-monedas@example.com')
    borrower = create_user(email='prestamos-monedas-deudor@example.com')
    authenticate(client, borrower)
    fund_user(lender.id, currency='USD', key='prestamos-3')
    create_loan(lender, borrower, key='prestamos-3', currency='USD')

    response = client.get('/api/v1/reports/loans/?currency=ARS')

    assert response.data['as_borrower']['active_loans'] == 0
    assert response.data['as_borrower']['outstanding_amount'] == '0.00'

    response_usd = client.get('/api/v1/reports/loans/?currency=USD')

    assert response_usd.data['as_borrower']['active_loans'] == 1


def test_loans_report_does_not_show_other_users_loans(client):
    """Cada usuario ve solo sus préstamos."""
    lender = create_user(email='prestamos-ajeno@example.com')
    borrower = create_user(email='prestamos-ajeno-deudor@example.com')
    other = create_user(email='prestamos-ajeno-tercero@example.com')
    authenticate(client, other)
    fund_user(lender.id, key='prestamos-4')
    create_loan(lender, borrower, key='prestamos-4')

    response = client.get('/api/v1/reports/loans/?currency=ARS')

    assert response.data['as_borrower']['active_loans'] == 0
    assert response.data['as_lender']['active_loans'] == 0
    assert response.data['as_borrower']['next_installments'] == []
