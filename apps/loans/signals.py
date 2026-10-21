"""Señales de la app loans (AGENTS §5.3).

Las define la app emisora: `notifications` conecta sus receptores a estas
señales. Solo llevan identificadores, nunca datos del negocio.
"""

from django.dispatch import Signal

# Cuota que está por vencer (la recibe el prestatario).
installment_due_soon = Signal()

# Cuota vencida (la reciben el prestatario y el prestamista).
installment_overdue = Signal()
