"""Tareas Celery de la app de investments.

La task es un adaptador delgado: delega en `services.settle_matured_positions` y
no repite ninguna regla de negocio (AGENTS §5.1). El management command
`settle_investments` usa el mismo service, así que ambas vías se comportan
igual.
"""

import logging
from datetime import date

from celery import shared_task
from django.utils import timezone

from apps.investments.services import settle_matured_positions

logger = logging.getLogger(__name__)


@shared_task(name='apps.investments.tasks.settle_investments')
def settle_investments(today: date | None = None) -> int:
    """Liquida las posiciones de inversión cuya fecha de vencimiento ya pasó.

    Args:
        today: fecha de referencia; por defecto, la fecha local de hoy.

    Returns:
        La cantidad de posiciones liquidadas.
    """
    reference = today or timezone.localdate()
    settled = settle_matured_positions(today=reference)
    logger.info('Tarea settle_investments: count=%s date=%s', settled, reference)
    return settled
