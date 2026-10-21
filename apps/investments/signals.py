"""Señales de la app investments (AGENTS §5.3).

Las define la app emisora: `notifications` conecta sus receptores a esta señal.
"""

from django.dispatch import Signal

# Posición de inversión liquidada (la recibe el inversionista).
investment_settled = Signal()
