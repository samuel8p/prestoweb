"""Fixtures compartidas de los tests de identity."""

import pytest


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Limpia la caché de throttling entre tests para aislar los límites de tasa."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()
