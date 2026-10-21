"""Tests de la tarea de envío de emails de las notificaciones."""

from datetime import date
from decimal import Decimal

import pytest
from django.core import mail

from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db

EMAIL = 'notificado@example.com'


def create_user(email=EMAIL):
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


def create_loan_with_installment(lender, borrower):
    """Crea un préstamo aceptado y devuelve su primera cuota."""
    from apps.ledger.services import deposit
    from apps.loans.services import accept_offer
    from apps.offers.services import create_offer

    deposit(
        user_id=lender.id,
        currency='ARS',
        amount=Decimal('10000.00'),
        idempotency_key='notif-1',
    )
    offer = create_offer(
        lender_user_id=lender.id,
        amount=Decimal('3000.00'),
        currency='ARS',
        interest_rate=Decimal('24.00'),
        term_months=3,
    )
    loan = accept_offer(
        borrower_user_id=borrower.id,
        offer_id=offer.id,
        idempotency_key='notif-1-aceptar',
    )
    return loan.installments.order_by('number').first()


def create_notification(user, event_type, reference_id):
    """Crea un aviso pendiente para el usuario."""
    from apps.notifications.services import create_notification as service_create

    return service_create(
        user_id=user.id,
        event_type=event_type,
        reference_id=reference_id,
    )


def test_send_notification_email_sends_the_email():
    """La tarea manda el email del aviso al destinatario."""
    from apps.notifications.tasks import send_notification_email

    create_user()
    lender = create_user(email='notif-lender@example.com')
    borrower = create_user(email='notif-borrower@example.com')
    installment = create_loan_with_installment(lender, borrower)
    notification = create_notification(
        borrower,
        Notification.EventType.INSTALLMENT_DUE_SOON,
        installment.id,
    )

    sent = send_notification_email(str(notification.id))

    assert sent is True
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ['notif-borrower@example.com']
    assert 'vencer' in message.subject
    assert '1' in message.body
    assert message.body.strip()


def test_send_notification_email_marks_the_notification_as_sent():
    """Un aviso enviado queda en estado sent con la fecha de envío."""
    from apps.notifications.tasks import send_notification_email

    create_user()
    lender = create_user(email='notif-lender-2@example.com')
    borrower = create_user(email='notif-borrower-2@example.com')
    installment = create_loan_with_installment(lender, borrower)
    notification = create_notification(
        borrower,
        Notification.EventType.INSTALLMENT_DUE_SOON,
        installment.id,
    )

    send_notification_email(str(notification.id))

    notification.refresh_from_db()
    assert notification.status == Notification.Status.SENT
    assert notification.sent_at is not None
    assert notification.error == ''


def test_send_notification_email_does_not_send_the_same_notification_twice():
    """Un aviso ya enviado no se manda de nuevo."""
    from apps.notifications.tasks import send_notification_email

    create_user()
    lender = create_user(email='notif-lender-3@example.com')
    borrower = create_user(email='notif-borrower-3@example.com')
    installment = create_loan_with_installment(lender, borrower)
    notification = create_notification(
        borrower,
        Notification.EventType.INSTALLMENT_DUE_SOON,
        installment.id,
    )

    send_notification_email(str(notification.id))
    sent_again = send_notification_email(str(notification.id))

    assert sent_again is False
    assert len(mail.outbox) == 1


def test_send_notification_email_marks_the_notification_as_failed_on_smtp_error():
    """Un fallo de SMTP marca el aviso como fallido y no levanta una excepción."""
    from unittest.mock import patch

    from apps.notifications.tasks import send_notification_email

    create_user()
    lender = create_user(email='notif-lender-4@example.com')
    borrower = create_user(email='notif-borrower-4@example.com')
    installment = create_loan_with_installment(lender, borrower)
    notification = create_notification(
        borrower,
        Notification.EventType.INSTALLMENT_DUE_SOON,
        installment.id,
    )

    with patch(
        'apps.notifications.tasks.send_mail',
        side_effect=OSError('smtp caido'),
    ):
        sent = send_notification_email(str(notification.id))

    assert sent is False
    notification.refresh_from_db()
    assert notification.status == Notification.Status.FAILED
    assert notification.error
    assert len(mail.outbox) == 0


def test_send_notification_email_of_an_unknown_notification_does_nothing():
    """Un aviso que no existe no rompe la tarea."""
    from apps.notifications.tasks import send_notification_email

    sent = send_notification_email('99999999-9999-9999-9999-999999999999')

    assert sent is False
    assert len(mail.outbox) == 0
