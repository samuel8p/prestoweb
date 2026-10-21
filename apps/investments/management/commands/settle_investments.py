"""Management command que liquida las posiciones de inversión vencidas."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.investments.services import settle_matured_positions


class Command(BaseCommand):
    """Liquida las posiciones de inversión cuya fecha de vencimiento ya pasó."""

    help = 'Liquida las posiciones de inversión vencidas pagando capital e interés.'

    def handle(self, *args, **options):
        """Ejecuta la liquidación de las posiciones vencidas para la fecha de hoy."""
        today = timezone.localdate()
        settled = settle_matured_positions(today=today)
        self.stdout.write(self.style.SUCCESS(f'{settled} posición(es) liquidada(s) el {today}.'))
        return None
