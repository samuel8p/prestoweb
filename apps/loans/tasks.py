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
