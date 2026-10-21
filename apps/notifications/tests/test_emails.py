"""Tests del armado de los emails de las notificaciones."""

from datetime import date
from decimal import Decimal

import pytest

from apps.ledger.services import withdraw
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db


def create_user(email='emails@example.com'):
    """Crea un usuario con KYC aprobada."""
    from apps.identity.services import register_user, resolve_kyc, submit_kyc

    user = register_user(email=email, password='TestPass123!')
    verification = submit_kyc(user=user, documents={})
    resolve_kyc(
        verification_id=verification.id,
        status='approved',
        resolved_by_user_id=None,
    )
    return user


def create_installment(user, key='emails'):
    """Crea un préstamo y devuelve su primera cuota."""
    from apps.ledger.services import deposit
    from apps.loans.services import accept_offer
    from apps.offers.services import create_offer

    lender = create_user(email=f'{key}-prestamista@example.com')
    deposit(
        user_id=lender.id,
        currency='ARS',
        amount=Decimal('10000.00'),
        idempotency_key=f'{key}-fondos',
    )
    offer = create_offer(
        lender_user_id=lender.id,
        amount=Decimal('3000.00'),
        currency='ARS',
        interest_rate=Decimal('24.00'),
        term_months=3,
    )
    loan = accept_offer(
        borrower_user_id=user.id,
        offer_id=offer.id,
        idempotency_key=f'{key}-aceptar',
    )
    return loan.installments.order_by('number').first()


def test_build_email_of_a_due_soon_installment():
    """El email de la cuota por vencer menciona el número, el vencimiento y el importe."""
    from apps.notifications.emails import build_email
    from apps.notifications.tests.factories import NotificationFactory

    user = create_user()
    installment = create_installment(user)
    notification = NotificationFactory(
        user_id=user.id,
        event_type=Notification.EventType.INSTALLMENT_DUE_SOON,
        reference_id=installment.id,
    )

    subject, body = build_email(notification)

    assert 'vence' in subject
    assert f'cuota {installment.number}' in body
    assert str(installment.due_date) in body
    assert str(installment.amount) in body


def test_build_email_of_an_overdue_installment():
    """El email de la cuota vencida menciona el vencimiento."""
    from apps.notifications.emails import build_email
    from apps.notifications.tests.factories import NotificationFactory

    user = create_user(email='emails-vencida@example.com')
    installment = create_installment(user, key='emails-vencida')
    notification = NotificationFactory(
        user_id=user.id,
        event_type=Notification.EventType.INSTALLMENT_OVERDUE,
        reference_id=installment.id,
    )

    subject, body = build_email(notification)

    assert 'vencida' in subject
    assert 'venció' in body


def test_build_email_of_a_settled_investment():
    """El email de la inversión liquidada menciona el capital y el interés."""
    from apps.investments.services import open_position
    from apps.investments.tests.factories import InvestmentProductFactory
    from apps.ledger.services import deposit
    from apps.notifications.emails import build_email
    from apps.notifications.tests.factories import NotificationFactory

    user = create_user(email='emails-inversion@example.com')
    product = InvestmentProductFactory(
        term_days=365,
        annual_rate_tna=Decimal('12.00'),
        min_amount=Decimal('1000.00'),
    )
    deposit(
        user_id=user.id,
        currency='ARS',
        amount=Decimal('10000.00'),
        idempotency_key='emails-inversion-fondos',
    )
    position = open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='emails-inversion-apertura',
    )
    notification = NotificationFactory(
        user_id=user.id,
        event_type=Notification.EventType.INVESTMENT_SETTLED,
        reference_id=position.id,
    )

    subject, body = build_email(notification)

    assert 'liquidó' in subject
    assert '5000.00' in body
    assert str(position.interest_amount) in body


def test_build_email_of_a_budget_alert():
    """El email de la alerta de presupuesto menciona el gastado y el límite."""
    from apps.budgets.services import create_budget, create_category
    from apps.notifications.emails import build_email
    from apps.notifications.tests.factories import NotificationFactory

    user = create_user(email='emails-presupuesto@example.com')
    category = create_category(user_id=user.id, name='Comida')
    budget = create_budget(
        user_id=user.id,
        category_id=category.id,
        limit_amount=Decimal('100.00'),
        currency='ARS',
        alert_threshold=50,
    )
    from apps.budgets.selectors import budget_alert_reference

    reference_id = budget_alert_reference(
        budget_id=budget.id,
        year=date.today().year,
        month=date.today().month,
    )
    notification = NotificationFactory(
        user_id=user.id,
        event_type=Notification.EventType.BUDGET_ALERT,
        reference_id=reference_id,
    )

    subject, body = build_email(notification)

    assert 'umbral' in subject
    assert '100.00' in body


def test_build_email_falls_back_when_the_reference_does_not_exist():
    """Si la referencia no existe, el email es genérico."""
    from apps.notifications.emails import build_email
    from apps.notifications.tests.factories import NotificationFactory

    notification = NotificationFactory(
        user_id=create_user().id,
        event_type=Notification.EventType.BUDGET_ALERT,
    )

    subject, body = build_email(notification)

    assert subject == 'Presto: tenés un aviso'
    assert 'Presto' in body


def test_build_email_of_an_unknown_event_falls_back():
    """Un evento desconocido usa el email genérico."""
    from apps.notifications.emails import build_email
    from apps.notifications.tests.factories import NotificationFactory

    notification = NotificationFactory(user_id=create_user().id, event_type='otro_evento')

    subject, body = build_email(notification)

    assert subject == 'Presto: tenés un aviso'


def test_build_email_of_a_due_soon_installment_without_reference():
    """Si la cuota no existe, el email de cuota por vencer es genérico."""
    from apps.notifications.emails import build_email
    from apps.notifications.tests.factories import NotificationFactory

    notification = NotificationFactory(
        user_id=create_user().id,
        event_type=Notification.EventType.INSTALLMENT_DUE_SOON,
    )

    subject, body = build_email(notification)

    assert subject == 'Presto: tenés un aviso'
    assert 'cuota por vencer' in body


def test_build_email_of_an_overdue_installment_without_reference():
    """Si la cuota no existe, el email de cuota vencida es genérico."""
    from apps.notifications.emails import build_email
    from apps.notifications.tests.factories import NotificationFactory

    notification = NotificationFactory(
        user_id=create_user().id,
        event_type=Notification.EventType.INSTALLMENT_OVERDUE,
    )

    subject, body = build_email(notification)

    assert subject == 'Presto: tenés un aviso'
    assert 'cuota vencida' in body


def test_the_budget_alert_sends_an_email_with_the_amounts(django_capture_on_commit_callbacks):
    """La alerta manda un email con el gastado y el límite del presupuesto."""
    from django.core import mail

    from apps.budgets.services import categorize_movement, create_budget, create_category
    from apps.ledger.services import deposit
    from apps.notifications.models import Notification

    user = create_user(email='alerta-email@example.com')
    category = create_category(user_id=user.id, name='Comida')
    create_budget(
        user_id=user.id,
        category_id=category.id,
        limit_amount=Decimal('100.00'),
        currency='ARS',
        alert_threshold=50,
    )
    deposit(
        user_id=user.id,
        currency='ARS',
        amount=Decimal('1000.00'),
        idempotency_key='alerta-email-fondo',
    )
    movement = withdraw(
        user_id=user.id,
        currency='ARS',
        amount=Decimal('60.00'),
        idempotency_key='alerta-email-gasto',
    )
    mail.outbox.clear()

    with django_capture_on_commit_callbacks(execute=True):
        categorize_movement(
            user_id=user.id,
            ledger_transaction_id=movement.id,
            category_id=category.id,
        )

    alert = Notification.objects.get(event_type=Notification.EventType.BUDGET_ALERT)
    assert alert.status == Notification.Status.SENT
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ['alerta-email@example.com']
    assert '60.00' in mail.outbox[0].body
    assert '100.00' in mail.outbox[0].body


def test_settling_a_position_creates_the_notification_and_sends_the_email(
    django_capture_on_commit_callbacks,
):
    """La liquidación deja el aviso enviado y el email en la bandeja."""
    from datetime import date

    from django.core import mail

    from apps.investments.services import open_position, settle_matured_positions
    from apps.investments.tests.factories import InvestmentProductFactory
    from apps.ledger.services import deposit
    from apps.notifications.models import Notification

    user = create_user(email='notif-inversion-email@example.com')
    product = InvestmentProductFactory(
        term_days=365,
        annual_rate_tna=Decimal('12.00'),
        min_amount=Decimal('1000.00'),
    )
    deposit(
        user_id=user.id,
        currency='ARS',
        amount=Decimal('10000.00'),
        idempotency_key='notif-inversion-email-fondos',
    )
    position = open_position(
        user_id=user.id,
        product_id=product.id,
        amount=Decimal('5000.00'),
        idempotency_key='notif-inversion-email-apertura',
    )
    mail.outbox.clear()

    with django_capture_on_commit_callbacks(execute=True):
        settle_matured_positions(today=date(2030, 1, 1))

    notification = Notification.objects.get(
        user_id=user.id,
        event_type=Notification.EventType.INVESTMENT_SETTLED,
        reference_id=position.id,
    )
    assert notification.status == Notification.Status.SENT
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ['notif-inversion-email@example.com']
