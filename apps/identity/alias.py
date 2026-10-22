"""Reglas del alias público de un usuario.

El alias es el identificador por el que un usuario puede ser encontrado (para
mandarle plata o un aviso), así que tiene reglas estrictas: formato corto y
predecible, sin mayúsculas y sin palabras reservadas.
"""

import re

from apps.identity.exceptions import InvalidAlias

ALIAS_MIN_LENGTH = 6
ALIAS_MAX_LENGTH = 20

# Empieza y termina con letra o dígito; en el medio, dígitos, punto, guion o
# guion bajo.
ALIAS_PATTERN = re.compile(r'^[a-z0-9](?:[a-z0-9._-]{4,18})[a-z0-9]$')

# Palabras que no se pueden usar: rutas de la API, nombres de rol y palabras
# que un usuario podría confundir con el soporte o la administración.
RESERVED_ALIASES = frozenset(
    {
        'admin',
        'administrador',
        'api',
        'ayuda',
        'demo',
        'dev',
        'help',
        'login',
        'mail',
        'me',
        'moderador',
        'postmaster',
        'presto',
        'root',
        'soporte',
        'staff',
        'support',
        'superuser',
        'sistema',
        'system',
        'usuario',
        'www',
    }
)


def validate_alias(value: str) -> str:
    """Valida un alias y lo devuelve normalizado.

    El alias se guarda tal cual (sin espacios alrededor); el formato obliga a
    que ya venga en minúsculas.

    Args:
        value: el alias propuesto.

    Returns:
        El alias sin espacios alrededor.

    Raises:
        InvalidAlias: si el formato no se cumple o el alias está reservado.
    """
    alias = (value or '').strip()
    if not ALIAS_PATTERN.match(alias):
        raise InvalidAlias(
            'El alias debe tener entre 6 y 20 caracteres, empezar y terminar con '
            'una letra o un dígito y solo usar minúsculas, dígitos, punto, guion '
            'o guion bajo.'
        )
    if alias in RESERVED_ALIASES:
        raise InvalidAlias('Ese alias está reservado. Probá con otro.')
    return alias
