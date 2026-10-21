"""Configuración del proyecto Django.

Importa la app de Celery para que las tareas usen `shared_task` y el worker
arranque con el mismo settings que Django.
"""

from .celery import app as celery_app

__all__ = ('celery_app',)
