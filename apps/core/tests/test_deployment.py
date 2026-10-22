"""Tests de la configuración de despliegue (compose, health check y usuario sin root)."""

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
APP_SERVICES = ('web', 'worker', 'beat')


@pytest.fixture(scope='module')
def prod_compose():
    """Devuelve el compose de producción ya parseado."""
    return yaml.safe_load((ROOT / 'docker-compose.prod.yml').read_text(encoding='utf-8'))


def test_the_production_app_services_run_as_a_non_root_user(prod_compose):
    """web, worker y beat no corren como root."""
    for service in APP_SERVICES:
        assert prod_compose['services'][service]['user'] == 'presto'


def test_the_image_ends_as_a_non_root_user():
    """La imagen deja el proceso final con un usuario sin privilegios."""
    dockerfile = (ROOT / 'Dockerfile').read_text(encoding='utf-8')

    assert 'USER presto' in dockerfile
    assert 'useradd' in dockerfile


def test_the_image_keeps_the_writes_out_of_the_project_directory():
    """El bytecode, la cache de pytest, la de ruff y la cobertura no se
    escriben en el proyecto.

    En desarrollo el código llega como un volumen del host: el contenedor no
    puede escribir ahí.
    """
    dockerfile = (ROOT / 'Dockerfile').read_text(encoding='utf-8')

    assert 'PYTHONDONTWRITEBYTECODE=1' in dockerfile
    assert 'COVERAGE_FILE=' in dockerfile
    assert 'cache_dir=' in dockerfile
    assert 'RUFF_CACHE_DIR=' in dockerfile


def test_every_environment_variable_read_by_the_settings_is_documented():
    """Cada variable que leen los settings está en los archivos de ejemplo.

    Copiar `.env.example` tiene que bastar para saber qué se puede
    configurar: si una variable se lee y no está documentada, nadie la
    encuentra.
    """
    variables = set()
    for path in sorted((ROOT / 'config/settings').glob('*.py')):
        text = path.read_text(encoding='utf-8')
        variables.update(re.findall(r"os\.getenv\(\s*['\"]([A-Z_]+)['\"]", text))
        variables.update(re.findall(r"os\.environ\.get\(\s*['\"]([A-Z_]+)['\"]", text))

    examples = (ROOT / '.env.example').read_text(encoding='utf-8')
    examples += (ROOT / '.env.prod.example').read_text(encoding='utf-8')

    missing = [name for name in sorted(variables) if name not in examples]

    assert missing == []


def test_the_development_example_documents_the_demo_switches():
    """El ejemplo de desarrollo documenta el modo demo y el dinero simulado.

    Son las dos variables que el compose de desarrollo pasa al contenedor:
    sin documentar, no hay forma de saber que existen.
    """
    example = (ROOT / '.env.example').read_text(encoding='utf-8')

    assert 'DEMO_MODE=' in example
    assert 'LEDGER_SIMULATED_DEPOSITS_ENABLED=' in example


def test_the_dependencies_are_audited_in_the_ci():
    """La CI audita las dependencias conocidas de las librerías.

    `pip-audit` tiene que estar declarado como dependencia de desarrollo y
    la CI tiene que ejecutarlo: sin la puerta, una vulnerabilidad conocida
    entra sin que nadie lo note.
    """
    pyproject = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    workflow = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')

    assert 'pip-audit' in pyproject
    assert 'pip-audit' in workflow
    assert 'pip_audit' in workflow or 'pip-audit ' in workflow


def test_the_ci_runs_the_deploy_check_with_the_production_settings():
    """La CI corre el `check --deploy` con los settings de producción.

    Es la puerta que detecta un ajuste de producción que rompe una regla de
    seguridad (HSTS, cookies seguras, `ALLOWED_HOSTS`, `DEBUG`).
    """
    workflow = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')

    assert 'check --deploy' in workflow
    assert 'config.settings.production' in workflow


def command_text(service) -> str:
    """Devuelve el comando de un servicio del compose como texto."""
    command = service['command']
    if isinstance(command, list):
        return ' '.join(command)
    return command


def test_the_production_concurrency_is_configurable_with_a_low_default(prod_compose):
    """Los workers de gunicorn y la concurrencia de Celery se configuran por entorno.

    La VM de Oracle Cloud tiene entre 1 y 2 OCPU: el número de procesos tiene
    que poder ajustarse sin tocar el compose, y el default tiene que ser
    bajo para no ahogar una VM chica.
    """
    web_command = command_text(prod_compose['services']['web'])
    worker_command = command_text(prod_compose['services']['worker'])

    assert 'GUNICORN_WORKERS' in web_command
    assert 'CELERY_WORKER_CONCURRENCY' in worker_command
    assert '--concurrency' in worker_command


def test_the_production_defaults_are_low(prod_compose):
    """Los defaults de concurrencia son bajos (1-3) para una VM chica."""
    web_command = command_text(prod_compose['services']['web'])
    worker_command = command_text(prod_compose['services']['worker'])

    gunicorn_default = web_command.split('GUNICORN_WORKERS:-')[1].split('}')[0]
    celery_default = worker_command.split('CELERY_WORKER_CONCURRENCY:-')[1].split('}')[0]

    assert 1 <= int(gunicorn_default) <= 3
    assert 1 <= int(celery_default) <= 3


def run_entrypoint(tmp_path, role, environment):
    """Ejecuta el entrypoint con un `celery` falso y devuelve sus argumentos."""
    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    fake = fake_bin / 'celery'
    fake.write_text('#!/bin/sh\necho "celery $@"\n', encoding='utf-8')
    fake.chmod(0o755)

    env = {**os.environ, 'PATH': f'{fake_bin}{os.pathsep}{os.environ["PATH"]}', **environment}
    result = subprocess.run(
        ['sh', str(ROOT / 'deploy/entrypoint.sh'), role],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_the_worker_starts_without_the_embedded_beat_by_default(tmp_path):
    """Sin `CELERY_EMBED_BEAT` el worker no lleva el beat embebido."""
    output = run_entrypoint(tmp_path, 'worker', {'CELERY_EMBED_BEAT': 'false'})

    assert '-B' not in output


def test_the_worker_starts_with_the_embedded_beat(tmp_path):
    """Con `CELERY_EMBED_BEAT=true` el worker arranca con el beat embebido."""
    output = run_entrypoint(tmp_path, 'worker', {'CELERY_EMBED_BEAT': 'true'})

    assert '-B' in output
    assert 'celery' in output


def test_the_embedded_beat_keeps_the_schedule_of_the_project(tmp_path):
    """El beat embebido usa el schedule del proyecto (`config/celery.py`)."""
    output = run_entrypoint(tmp_path, 'worker', {'CELERY_EMBED_BEAT': 'true'})

    assert '-A' in output
    assert 'config' in output
