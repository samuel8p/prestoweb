"""Tests de la configuración de Celery (cola de tareas y scheduler).

La app de Celery es la infraestructura que usan las tareas periódicas: broker
en Redis, descubrimiento automático de `tasks.py` por app y un beat schedule con
las tareas diarias del negocio.

Este archivo solo toca `config.celery` y los settings: no importa apps de
dominio, porque `core` no puede importarlas (contrato `core-isolation`).
"""

from django.conf import settings


def get_celery_app():
    """Devuelve la app de Celery del proyecto."""
    from config.celery import app

    return app


def test_celery_app_is_configured_with_the_project_name():
    """La app de Celery se llama `presto`."""
    assert get_celery_app().main == 'presto'


def test_celery_app_reads_the_broker_from_settings():
    """El broker sale de los settings y no tiene un valor hardcodeado."""
    app = get_celery_app()

    assert app.conf.broker_url == settings.CELERY_BROKER_URL


def test_the_default_broker_is_redis():
    """Sin configuración explícita, el broker es el Redis del proyecto."""
    from config.settings.base import CELERY_BROKER_URL

    assert CELERY_BROKER_URL.startswith('redis://')


def test_celery_app_is_configured_for_django():
    """La app tiene el fixup de Django: eso habilita el descubrimiento de `tasks.py`."""
    app = get_celery_app()

    assert 'celery.fixups.django:fixup' in app.fixups
    assert app.autodiscover_tasks is not None


def test_celery_does_not_store_task_results():
    """No hay result backend persistente: las tareas no guardan resultados."""
    app = get_celery_app()

    assert app.conf.task_ignore_result is True
    assert not settings.CELERY_RESULT_BACKEND


def test_celery_uses_utc():
    """Celery corre en UTC, igual que el resto del proyecto."""
    assert get_celery_app().conf.timezone == 'UTC'


def test_beat_schedule_contains_the_daily_tasks():
    """El beat schedule programa las dos tareas periódicas del negocio."""
    schedule = get_celery_app().conf.beat_schedule

    assert schedule['mark_overdue_loans_diario']['task'] == 'apps.loans.tasks.mark_overdue_loans'
    assert (
        schedule['settle_investments_diario']['task'] == 'apps.investments.tasks.settle_investments'
    )


def test_beat_schedule_runs_the_daily_tasks_at_the_agreed_utc_times():
    """`mark_overdue_loans` a las 00:05 UTC y `settle_investments` a las 00:15 UTC."""
    schedule = get_celery_app().conf.beat_schedule

    mark_overdue = schedule['mark_overdue_loans_diario']['schedule']
    assert mark_overdue.hour == {0}
    assert mark_overdue.minute == {5}

    settle = schedule['settle_investments_diario']['schedule']
    assert settle.hour == {0}
    assert settle.minute == {15}


def test_test_settings_run_celery_eagerly():
    """En los tests las tareas corren en el proceso, sin depender de Redis."""
    assert settings.CELERY_TASK_ALWAYS_EAGER is True
    assert settings.CELERY_TASK_EAGER_PROPAGATES is True
