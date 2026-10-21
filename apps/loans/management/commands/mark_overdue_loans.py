"""Management command que marca las cuotas vencidas."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.loans.services import mark_overdue


class Command(BaseCommand):
    """Marca como vencidas las cuotas que pasaron su fecha de vencimiento."""

    help = 'Marca como vencidas las cuotas vencidas y los préstamos en mora.'

    def handle(self, *args, **options):
        """Ejecuta el marcado de cuotas vencidas para la fecha de hoy."""
        today = timezone.localdate()
        marked = mark_overdue(today=today)
        self.stdout.write(
            self.style.SUCCESS(f'{marked} cuota(s) marcada(s) como vencida(s) el {today}.')
        )
        return None
