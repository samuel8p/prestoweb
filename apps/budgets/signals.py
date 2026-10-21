"""Señales de la app budgets (AGENTS §5.3).

Las define la app emisora: `notifications` conecta sus receptores a esta señal.
"""

from django.dispatch import Signal

# El gasto de un presupuesto cruzó el umbral de alerta.
budget_alert = Signal()
