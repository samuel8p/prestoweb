"""Tests de la configuración de despliegue (compose, health check y usuario sin root)."""

import re
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
