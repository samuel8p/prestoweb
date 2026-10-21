"""Tests del cálculo del gasto acumulado por categoría y moneda."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from apps.budgets.tests.factories import create_approved_user

pytestmark = pytest.mark.django_db


def fund_user(user_id, amount='10000.00', currency='ARS', key='fund'):
    """Deposita fondos simulados en la billetera del usuario."""
    from apps.ledger.services import deposit

    return deposit(
        user_id=user_id,
        currency=currency,
        amount=Decimal(amount),
        idempotency_key=key,
    )


def make_withdrawal(user_id, amount='100.00', currency='ARS', key='gasto'):
    """Retira fondos de la billetera del usuario."""
    from apps.ledger.services import withdraw

    return withdraw(
        user_id=user_id,
        currency=currency,
        amount=Decimal(amount),
        idempotency_key=key,
    )


def current_month():
    """Devuelve el año y el mes (UTC) del momento actual."""
    now = datetime.now(UTC)
    return now.year, now.month


def previous_month():
    """Devuelve el año y el mes (UTC) del mes anterior."""
    now = datetime.now(UTC) - timedelta(days=32)
    return now.year, now.month


def test_monthly_spending_sums_the_categorized_withdrawals():
    """El gasto del mes es la suma de los movimientos categorizados."""
    from apps.budgets.selectors import get_monthly_spending
    from apps.budgets.services import categorize_movement

    user = create_approved_user(email='gasto-mes@example.com')
    from apps.budgets.tests.factories import CategoryFactory

    category = CategoryFactory(user_id=user.id)
    fund_user(user.id, key='gasto-1')
    first = make_withdrawal(user.id, amount='100.00', key='gasto-1-a')
    second = make_withdrawal(user.id, amount='250.50', key='gasto-1-b')
    for movement in (first, second):
        categorize_movement(
            user_id=user.id,
            ledger_transaction_id=movement.id,
            category_id=category.id,
        )
    year, month = current_month()

    spent = get_monthly_spending(
        user_id=user.id,
        category_id=category.id,
        currency='ARS',
        year=year,
        month=month,
    )

    assert spent == Decimal('350.50')


def test_monthly_spending_ignores_movements_without_a_category():
    """Un movimiento sin categoría no cuenta en ningún presupuesto."""
    from apps.budgets.selectors import get_monthly_spending
    from apps.budgets.tests.factories import CategoryFactory

    user = create_approved_user(email='gasto-sin-categoria@example.com')
    category = CategoryFactory(user_id=user.id)
    fund_user(user.id, key='gasto-2')
    make_withdrawal(user.id, amount='500.00', key='gasto-2-sin-categoria')
    year, month = current_month()

    spent = get_monthly_spending(
        user_id=user.id,
        category_id=category.id,
        currency='ARS',
        year=year,
        month=month,
    )

    assert spent == Decimal('0.00')


def test_monthly_spending_only_counts_the_requested_currency():
    """El presupuesto en ARS no cuenta los gastos en USD."""
    from apps.budgets.selectors import get_monthly_spending
    from apps.budgets.services import categorize_movement
    from apps.budgets.tests.factories import CategoryFactory

    user = create_approved_user(email='gasto-monedas@example.com')
    category = CategoryFactory(user_id=user.id)
    fund_user(user.id, key='gasto-3-ars')
    fund_user(user.id, currency='USD', key='gasto-3-usd')
    in_ars = make_withdrawal(user.id, amount='100.00', currency='ARS', key='gasto-3-ars-g')
    in_usd = make_withdrawal(user.id, amount='50.00', currency='USD', key='gasto-3-usd-g')
    for movement in (in_ars, in_usd):
        categorize_movement(
            user_id=user.id,
            ledger_transaction_id=movement.id,
            category_id=category.id,
        )
    year, month = current_month()

    spent_ars = get_monthly_spending(
        user_id=user.id,
        category_id=category.id,
        currency='ARS',
        year=year,
        month=month,
    )
    spent_usd = get_monthly_spending(
        user_id=user.id,
        category_id=category.id,
        currency='USD',
        year=year,
        month=month,
    )

    assert spent_ars == Decimal('100.00')
    assert spent_usd == Decimal('50.00')


def test_monthly_spending_ignores_other_months():
    """Un movimiento cuenta en su mes y no en otro período."""
    from apps.budgets.selectors import get_monthly_spending
    from apps.budgets.services import categorize_movement
    from apps.budgets.tests.factories import CategoryFactory

    user = create_approved_user(email='gasto-mes-anterior@example.com')
    category = CategoryFactory(user_id=user.id)
    fund_user(user.id, key='gasto-4')
    movement = make_withdrawal(user.id, amount='300.00', key='gasto-4-gasto')
    categorize_movement(
        user_id=user.id,
        ledger_transaction_id=movement.id,
        category_id=category.id,
    )
    year, month = current_month()
    other_year, other_month = previous_month()

    spent = get_monthly_spending(
        user_id=user.id,
        category_id=category.id,
        currency='ARS',
        year=year,
        month=month,
    )
    spent_other_month = get_monthly_spending(
        user_id=user.id,
        category_id=category.id,
        currency='ARS',
        year=other_year,
        month=other_month,
    )

    assert spent == Decimal('300.00')
    assert spent_other_month == Decimal('0.00')


def test_monthly_spending_counts_only_the_interest_of_a_loan_payment():
    """El pago de una cuota suma solo el interés, no el capital."""
    from apps.budgets.selectors import get_monthly_spending
    from apps.budgets.services import categorize_movement
    from apps.budgets.tests.factories import CategoryFactory
    from apps.loans.services import accept_offer, pay_installment
    from apps.offers.services import create_offer

    lender = create_approved_user(email='prestamista-gasto@example.com')
    borrower = create_approved_user(email='prestatario-gasto@example.com')
    category = CategoryFactory(user_id=borrower.id)
    offer = create_offer(
        lender_user_id=lender.id,
        amount=Decimal('3000.00'),
        currency='ARS',
        interest_rate=Decimal('24.00'),
        term_months=3,
    )
    fund_user(lender.id, key='gasto-5')
    fund_user(borrower.id, key='gasto-5-prestatario')
    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='gasto-5-aceptar',
    )
    installment = pay_installment(
        loan_id=loan.id,
        number=1,
        borrower_user_id=borrower.id,
    )
    categorize_movement(
        user_id=borrower.id,
        ledger_transaction_id=installment.ledger_transaction_id,
        category_id=category.id,
    )
    year, month = current_month()

    spent = get_monthly_spending(
        user_id=borrower.id,
        category_id=category.id,
        currency='ARS',
        year=year,
        month=month,
    )

    assert spent == installment.interest_amount
    assert spent < installment.amount


def test_monthly_spending_ignores_a_reversed_movement():
    """Un movimiento que se revirtió después de categorizar deja de contar."""
    from apps.budgets.selectors import get_monthly_spending
    from apps.budgets.services import categorize_movement
    from apps.budgets.tests.factories import CategoryFactory
    from apps.ledger.services import reverse_transaction

    user = create_approved_user(email='gasto-revertido@example.com')
    category = CategoryFactory(user_id=user.id)
    fund_user(user.id, key='gasto-6')
    movement = make_withdrawal(user.id, amount='400.00', key='gasto-6-gasto')
    categorize_movement(
        user_id=user.id,
        ledger_transaction_id=movement.id,
        category_id=category.id,
    )
    reverse_transaction(transaction_id=movement.id, staff_user_id=user.id)
    year, month = current_month()

    spent = get_monthly_spending(
        user_id=user.id,
        category_id=category.id,
        currency='ARS',
        year=year,
        month=month,
    )

    assert spent == Decimal('0.00')


def test_monthly_spending_resolves_the_movements_in_one_batch():
    """El cálculo no hace una consulta por movimiento."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    from apps.budgets.selectors import get_monthly_spending
    from apps.budgets.services import categorize_movement
    from apps.budgets.tests.factories import CategoryFactory

    user = create_approved_user(email='gasto-lote@example.com')
    category = CategoryFactory(user_id=user.id)
    fund_user(user.id, key='gasto-7')
    for index in range(5):
        movement = make_withdrawal(user.id, amount='10.00', key=f'gasto-7-{index}')
        categorize_movement(
            user_id=user.id,
            ledger_transaction_id=movement.id,
            category_id=category.id,
        )
    year, month = current_month()

    def spending():
        return get_monthly_spending(
            user_id=user.id,
            category_id=category.id,
            currency='ARS',
            year=year,
            month=month,
        )

    with CaptureQueriesContext(connection) as queries_with_five:
        spent = spending()

    for index in range(5, 10):
        movement = make_withdrawal(user.id, amount='10.00', key=f'gasto-7-{index}')
        categorize_movement(
            user_id=user.id,
            ledger_transaction_id=movement.id,
            category_id=category.id,
        )

    with CaptureQueriesContext(connection) as queries_with_ten:
        spent = spending()

    assert spent == Decimal('100.00')
    assert len(queries_with_ten) == len(queries_with_five)


def test_budget_status_reports_the_spent_amount_and_the_remaining():
    """El estado del presupuesto informa gastado, límite y saldo."""
    from apps.budgets.selectors import get_budget_status
    from apps.budgets.services import categorize_movement, create_budget
    from apps.budgets.tests.factories import CategoryFactory

    user = create_approved_user(email='estado-presupuesto@example.com')
    category = CategoryFactory(user_id=user.id)
    budget = create_budget(
        user_id=user.id,
        category_id=category.id,
        limit_amount=Decimal('1000.00'),
        currency='ARS',
        alert_threshold=80,
    )
    fund_user(user.id, key='estado-1')
    movement = make_withdrawal(user.id, amount='250.00', key='estado-1-gasto')
    categorize_movement(
        user_id=user.id,
        ledger_transaction_id=movement.id,
        category_id=category.id,
    )
    year, month = current_month()

    status = get_budget_status(budget=budget, year=year, month=month)

    assert status['spent_amount'] == Decimal('250.00')
    assert status['limit_amount'] == Decimal('1000.00')
    assert status['remaining_amount'] == Decimal('750.00')
    assert status['threshold_amount'] == Decimal('800.00')
    assert status['alert_triggered'] is False
    assert status['currency'] == 'ARS'


def test_budget_status_triggers_the_alert_at_the_threshold():
    """La alerta se dispara cuando el gasto alcanza el umbral configurado."""
    from apps.budgets.selectors import get_budget_status
    from apps.budgets.services import categorize_movement, create_budget
    from apps.budgets.tests.factories import CategoryFactory

    user = create_approved_user(email='estado-alerta@example.com')
    category = CategoryFactory(user_id=user.id)
    budget = create_budget(
        user_id=user.id,
        category_id=category.id,
        limit_amount=Decimal('1000.00'),
        currency='ARS',
        alert_threshold=80,
    )
    fund_user(user.id, key='estado-2')
    movement = make_withdrawal(user.id, amount='800.00', key='estado-2-gasto')
    categorize_movement(
        user_id=user.id,
        ledger_transaction_id=movement.id,
        category_id=category.id,
    )
    year, month = current_month()

    status = get_budget_status(budget=budget, year=year, month=month)

    assert status['alert_triggered'] is True
