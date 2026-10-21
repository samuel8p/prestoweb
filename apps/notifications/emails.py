"""Armado de los emails de las notificaciones.

Son emails en español, en texto plano y **sin datos sensibles**: no se
incluyen saldos completos ni datos de KYC, solo lo del evento.
"""

from apps.notifications.models import Notification

SUBJECT_FALLBACK = 'Presto: tenés un aviso'


def build_email(notification: Notification) -> tuple[str, str]:
    """Arma el asunto y el cuerpo del email de un aviso.

    Args:
        notification: el aviso a enviar.

    Returns:
        Tupla con el asunto y el cuerpo del email.
    """
    if notification.event_type == Notification.EventType.INSTALLMENT_DUE_SOON:
        return _installment_due_soon_email(notification)
    if notification.event_type == Notification.EventType.INSTALLMENT_OVERDUE:
        return _installment_overdue_email(notification)
    if notification.event_type == Notification.EventType.INVESTMENT_SETTLED:
        return _investment_settled_email(notification)
    return SUBJECT_FALLBACK, 'Tenés un aviso nuevo en Presto.\n'


def _installment_due_soon_email(notification: Notification) -> tuple[str, str]:
    """Email de la cuota que está por vencer."""
    from apps.loans.selectors import get_installment

    installment = get_installment(notification.reference_id)
    if installment is None:
        return SUBJECT_FALLBACK, 'Tenés una cuota por vencer en Presto.\n'
    body = (
        'Hola,\n\n'
        f'La cuota {installment.number} de tu préstamo vence el {installment.due_date}.\n'
        f'El importe de la cuota es {installment.amount} {installment.loan.currency}.\n\n'
        'Podés ver el detalle de tu préstamo desde Presto.\n'
    )
    return 'Presto: tenés una cuota por vencer', body


def _installment_overdue_email(notification: Notification) -> tuple[str, str]:
    """Email de la cuota vencida."""
    from apps.loans.selectors import get_installment

    installment = get_installment(notification.reference_id)
    if installment is None:
        return SUBJECT_FALLBACK, 'Tenés una cuota vencida en Presto.\n'
    body = (
        'Hola,\n\n'
        f'La cuota {installment.number} de tu préstamo venció el {installment.due_date}.\n'
        f'El importe de la cuota es {installment.amount} {installment.loan.currency}.\n\n'
        'Podés ver el detalle de tu préstamo desde Presto.\n'
    )
    return 'Presto: tenés una cuota vencida', body


def _investment_settled_email(notification: Notification) -> tuple[str, str]:
    """Email de la inversión liquidada."""
    from apps.investments.selectors import get_position_for_user

    position = get_position_for_user(
        position_id=notification.reference_id,
        user_id=notification.user_id,
    )
    if position is None:
        return SUBJECT_FALLBACK, 'Tenés una inversión liquidada en Presto.\n'
    body = (
        'Hola,\n\n'
        f'Tu inversión por {position.amount} {position.product.currency} se liquidó.\n'
        f'El interés que ganaste fue de {position.interest_amount} '
        f'{position.product.currency}.\n\n'
        'Podés ver tus posiciones desde Presto.\n'
    )
    return 'Presto: tu inversión se liquidó', body
