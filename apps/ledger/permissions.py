"""Permisos y límites de tasa de la app ledger."""

from rest_framework.throttling import ScopedRateThrottle


class AliasLookupThrottle(ScopedRateThrottle):
    """Limita las búsquedas por alias a 5 por minuto (anti-enumeración).

    El scope lo define la vista con `throttle_scope = 'alias_lookup'`. Es
    más estricto que el login a propósito: por el alias se puede averiguar
    si alguien tiene cuenta y en qué monedas opera.
    """
