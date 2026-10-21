"""System checks de la app ledger."""

from django.conf import settings
from django.core.checks import Error


def check_simulated_deposits_disabled(app_configs, **kwargs):
    """Falla si los depósitos simulados están habilitados en producción.

    El entorno se determina con ``DJANGO_ENV``, nunca con ``DEBUG``: un
    ``DEBUG=False`` en staging no habilita los depósitos simulados.

    La única excepción es el **modo demo** (``DEMO_MODE=true``): ahí los
    depósitos simulados están abiertos a propósito y el check los deja pasar.
    """
    errors = []
    if (
        settings.DJANGO_ENV == 'production'
        and settings.LEDGER_SIMULATED_DEPOSITS_ENABLED
        and not settings.DEMO_MODE
    ):
        errors.append(
            Error(
                'LEDGER_SIMULATED_DEPOSITS_ENABLED no puede estar activo en producción.',
                hint=(
                    'Desactivá la variable de entorno LEDGER_SIMULATED_DEPOSITS_ENABLED '
                    'o activá DEMO_MODE=true si es un despliegue de demostración.'
                ),
                id='ledger.E001',
            )
        )
    return errors
