"""Tests de la documentación: los ADRs existen y están enlazados."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
ADR_DIR = ROOT / 'docs/adr'
ARCHITECTURE = ROOT / 'docs/architecture.md'
REQUIRED_SECTIONS = ('## Contexto', '## Decisión', '## Consecuencias')


@pytest.fixture(scope='module')
def architecture() -> str:
    """Devuelve el contenido de la documentación de arquitectura."""
    return ARCHITECTURE.read_text(encoding='utf-8')


def test_the_architecture_document_exists(architecture):
    """La documentación de arquitectura existe y no está vacía."""
    assert ARCHITECTURE.exists()
    assert len(architecture) > 2000


@pytest.mark.parametrize('adr_path', sorted(ADR_DIR.glob('*.md')), ids=lambda path: path.name)
def test_every_adr_is_linked_from_the_architecture_document(adr_path, architecture):
    """Cada ADR está enlazado desde la documentación de arquitectura."""
    assert adr_path.name in architecture


@pytest.mark.parametrize('adr_path', sorted(ADR_DIR.glob('*.md')), ids=lambda path: path.name)
def test_every_adr_has_the_expected_sections(adr_path):
    """Cada ADR tiene contexto, decisión y consecuencias."""
    content = adr_path.read_text(encoding='utf-8')

    for section in REQUIRED_SECTIONS:
        assert section in content, f'falta la sección {section} en {adr_path.name}'


def test_the_architecture_document_lists_every_app(architecture):
    """La documentación de arquitectura menciona todas las apps del proyecto."""
    from django.apps import apps

    missing = [
        config.label
        for config in sorted(apps.get_app_configs(), key=lambda config: config.label)
        if config.name.startswith('apps.') and f'`{config.label}`' not in architecture
    ]

    assert missing == []
