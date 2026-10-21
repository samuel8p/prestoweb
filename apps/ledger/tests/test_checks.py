"""Tests del system check de depósitos simulados (AGENTS §Reglas del ledger 5)."""

from apps.ledger.checks import check_simulated_deposits_disabled


def test_check_fails_when_enabled_in_production(settings):
    """Con el flag activo en producción el check falla."""
    settings.DJANGO_ENV = 'production'
    settings.LEDGER_SIMULATED_DEPOSITS_ENABLED = True

    errors = check_simulated_deposits_disabled(None)

    assert len(errors) == 1
    assert errors[0].id == 'ledger.E001'


def test_check_passes_when_disabled_in_production(settings):
    """Con el flag apagado en producción el check pasa."""
    settings.DJANGO_ENV = 'production'
    settings.LEDGER_SIMULATED_DEPOSITS_ENABLED = False

    assert check_simulated_deposits_disabled(None) == []


def test_check_passes_outside_production(settings):
    """Fuera de producción el flag puede estar activo."""
    settings.DJANGO_ENV = 'local'
    settings.LEDGER_SIMULATED_DEPOSITS_ENABLED = True

    assert check_simulated_deposits_disabled(None) == []


def test_check_does_not_rely_on_debug(settings):
    """El check usa DJANGO_ENV, no DEBUG."""
    settings.DJANGO_ENV = 'production'
    settings.DEBUG = False
    settings.LEDGER_SIMULATED_DEPOSITS_ENABLED = True

    errors = check_simulated_deposits_disabled(None)

    assert len(errors) == 1
