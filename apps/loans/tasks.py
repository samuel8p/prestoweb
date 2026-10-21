"""Tareas Celery de la app de loans.

La task es un adaptador delgado: delega en `services.mark_overdue` y no repite
ninguna regla de negocio (AGENTS §5.1). El management command
`mark_overdue_loans` usa el mismo service, así que ambas vías se comportan
igual.
"""

import logging
from datetime import date

from celery import shared_task
from django.utils import timezone

from apps.loans import selectors, signals
from apps.loans.services import mark_overdue

logger = logging.getLogger(__name__)


@shared_task(name='apps.loans.tasks.mark_overdue_loans')
def mark_overdue_loans(today: date | None = None) -> int:
    """Marca como vencidas las cuotas vencidas y los préstamos en mora.

    Args:
        today: fecha de referencia; por defecto, la fecha local de hoy.

    Returns:
        La cantidad de cuotas marcadas como vencidas.
    """
    reference = today or timezone.localdate()
    marked = mark_overdue(today=reference)
    logger.info('Tarea mark_overdue_loans: count=%s date=%s', marked, reference)
    return marked


@shared_task(name='apps.loans.tasks.notify_installments_due_soon')
def notify_installments_due_soon(today: date | None = None) -> int:
    """Avisa al prestatario de las cuotas que vencen en los próximos días.

    Args:
        today: fecha de referencia; por defecto, la fecha local de hoy.

    Returns:
        La cantidad de avisos generados.
    """
    reference = today or timezone.localdate()
    count = 0
    for installment in selectors.list_installments_due_soon(today=reference):
        signals.installment_due_soon.send(
            sender=None,
            user_id=installment.loan.borrower_user_id,
            reference_id=installment.id,
        )
        count += 1
    logger.info('Avisos de cuota por vencer: count=%s date=%s', count, reference)
    return count


@shared_task(name='apps.loans.tasks.notify_overdue_installments')
def notify_overdue_installments(today: date | None = None) -> int:
    """Avisa al prestatario y al prestamista de las cuotas vencidas.

    Args:
        today: fecha de referencia; por defecto, la fecha local de hoy.

    Returns:
        La cantidad de avisos generados.
    """
    reference = today or timezone.localdate()
    count = 0
    for installment in selectors.list_overdue_installments(today=reference):
        signals.installment_overdue.send(
            sender=None,
            user_id=installment.loan.borrower_user_id,
            reference_id=installment.id,
        )
        signals.installment_overdue.send(
            sender=None,
            user_id=installment.loan.lender_user_id,
            reference_id=installment.id,
        )
        count += 2
    logger.info('Avisos de cuota vencida: count=%s date=%s', count, reference)
    return count
