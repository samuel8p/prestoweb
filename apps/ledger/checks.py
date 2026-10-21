"""System checks de la app ledger."""

from django.conf import settings
from django.core.checks import Error


def check_simulated_deposits_disabled(app_configs, **kwargs):
    """Falla si los depósitos simulados están habilitados en producción.

    El entorno se determina con ``DJANGO_ENV``, nunca con ``DEBUG``: un
    ``DEBUG=False`` en staging no habilita los depósitos simulados.
    """
    errors = []
    if settings.DJANGO_ENV == 'production' and settings.LEDGER_SIMULATED_DEPOSITS_ENABLED:
        errors.append(
            Error(
                'LEDGER_SIMULATED_DEPOSITS_ENABLED no puede estar activo en producción.',
                hint='Desactivá la variable de entorno LEDGER_SIMULATED_DEPOSITS_ENABLED.',
                id='ledger.E001',
            )
        )
    return errors
