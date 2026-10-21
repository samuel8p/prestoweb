"""Tests del modo demo: setting DEMO_MODE y su efecto en los depósitos simulados."""

import os
import subprocess
import sys


def read_settings(**environment: str) -> dict:
    """Lee dos settings de Django con ese entorno, en un subproceso.

    Args:
        environment: variables de entorno para el subproceso.

    Returns:
        Dict con `DEMO_MODE` y `LEDGER_SIMULATED_DEPOSITS_ENABLED`.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(('EMAIL_', 'DEMO_', 'LEDGER_'))
    }
    env.update(environment)
    env['DJANGO_SETTINGS_MODULE'] = 'config.settings.base'
    result = subprocess.run(
        [
            sys.executable,
            '-c',
            'from django.conf import settings;'
            ' print(settings.DEMO_MODE);'
            ' print(settings.LEDGER_SIMULATED_DEPOSITS_ENABLED)',
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    demo_mode, simulated = result.stdout.strip().splitlines()
    return {
        'DEMO_MODE': demo_mode == 'True',
        'LEDGER_SIMULATED_DEPOSITS_ENABLED': simulated == 'True',
    }


def test_demo_mode_is_disabled_by_default():
    """Sin DEMO_MODE en el entorno, el modo demo está apagado."""
    assert read_settings()['DEMO_MODE'] is False


def test_demo_mode_turns_on_the_simulated_deposits():
    """Con DEMO_MODE=true los depósitos y retiros simulados quedan habilitados."""
    settings = read_settings(DEMO_MODE='true')

    assert settings['DEMO_MODE'] is True
    assert settings['LEDGER_SIMULATED_DEPOSITS_ENABLED'] is True
