from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
    verbose_name = 'Notifications'

    def ready(self):
        """Conecta los receptores de las señales de las apps emisoras."""
        from apps.notifications import receivers  # noqa: F401
