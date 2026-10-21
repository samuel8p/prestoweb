"""Tests del README: la documentación no puede quedar desactualizada."""

import re
from pathlib import Path

from django.urls import get_resolver

ROOT = Path(__file__).resolve().parents[3]


def api_endpoints() -> list[str]:
    """Devuelve las rutas de la API con los parámetros normalizados."""
    endpoints: list[str] = []

    def walk(resolver, prefix: str = '') -> None:
        for pattern in resolver.url_patterns:
            if hasattr(pattern, 'url_patterns'):
                walk(pattern, prefix + str(pattern.pattern))
                continue
            route = prefix + str(pattern.pattern)
            if not route.startswith('api/v1/'):
                continue
            route = re.sub(r'<uuid:[a-z_]+>', '{id}', route)
            route = re.sub(r'<int:[a-z_]+>', '{number}', route)
            endpoints.append('/' + route)

    walk(get_resolver())
    return sorted(endpoints)


def test_the_readme_documents_every_endpoint():
    """Cada endpoint de la API aparece en el README."""
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')

    missing = [endpoint for endpoint in api_endpoints() if endpoint not in readme]

    assert missing == []


def test_the_readme_documents_every_scheduled_task():
    """Cada tarea periódica del beat aparece en el README."""
    from config.celery import app

    readme = (ROOT / 'README.md').read_text(encoding='utf-8')

    missing = [task for task in app.conf.beat_schedule.values() if task['task'] not in readme]

    assert missing == []


def test_the_readme_documents_the_apps_of_the_project():
    """El README lista las apps que existen."""
    from django.apps import apps

    readme = (ROOT / 'README.md').read_text(encoding='utf-8')

    missing = [
        config.label
        for config in sorted(apps.get_app_configs(), key=lambda config: config.label)
        if config.name.startswith('apps.') and f'apps/{config.label}/' not in readme
    ]

    assert missing == []
