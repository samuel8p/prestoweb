from decimal import Decimal, ROUND_HALF_UP

ZERO = Decimal("0")
ONE = Decimal("1")

def round_two(value: Decimal) -> Decimal:
    """Redondeo a 2 decimales usando Decimal para evitar float."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def money(value) -> Decimal:
    """Convierta un valor a Decimal, aceptando str, int o float string."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))