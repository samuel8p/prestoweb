from django.apps import AppConfig
from django.core.checks import register


class LedgerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ledger'
    verbose_name = 'Ledger'

    def ready(self):
        """Registra los system checks de la app."""
        from apps.ledger.checks import check_simulated_deposits_disabled

        register(check_simulated_deposits_disabled)
