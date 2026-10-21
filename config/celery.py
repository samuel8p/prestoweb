"""Configuración de Celery: cola de tareas y scheduler de tareas periódicas.

El broker es Redis (AGENTS §3). No hay result backend persistente: las tareas
del proyecto no devuelven resultados, solo efectos.

El beat schedule corre las tareas periódicas del negocio una vez por día, en
UTC, que es la zona horaria del proyecto (`TIME_ZONE = 'UTC'`).

Requiere `DJANGO_SETTINGS_MODULE` en el entorno: `celery -A config worker`.
"""

from celery import Celery
from celery.schedules import crontab

app = Celery('presto')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'mark_overdue_loans_diario': {
        'task': 'apps.loans.tasks.mark_overdue_loans',
        'schedule': crontab(hour=0, minute=5),
    },
    'notify_installments_due_soon_diario': {
        'task': 'apps.loans.tasks.notify_installments_due_soon',
        'schedule': crontab(hour=0, minute=10),
    },
    'notify_overdue_installments_diario': {
        'task': 'apps.loans.tasks.notify_overdue_installments',
        'schedule': crontab(hour=0, minute=20),
    },
    'settle_investments_diario': {
        'task': 'apps.investments.tasks.settle_investments',
        'schedule': crontab(hour=0, minute=15),
    },
}
