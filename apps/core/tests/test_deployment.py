"""Tests de la configuración de despliegue (compose, health check y usuario sin root)."""

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
    """El bytecode, la cache de pytest y la cobertura no se escriben en el proyecto.

    En desarrollo el código llega como un volumen del host: el contenedor no
    puede escribir ahí.
    """
    dockerfile = (ROOT / 'Dockerfile').read_text(encoding='utf-8')

    assert 'PYTHONDONTWRITEBYTECODE=1' in dockerfile
    assert 'COVERAGE_FILE=' in dockerfile
    assert 'cache_dir=' in dockerfile
