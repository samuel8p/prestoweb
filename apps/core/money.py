from decimal import ROUND_HALF_UP, Decimal

from apps.core.exceptions import InvalidAmount

ZERO = Decimal('0')
ONE = Decimal('1')
HUNDRED = Decimal('100')
TWELVE = Decimal('12')


def round_two(value: Decimal) -> Decimal:
    """Redondeo a 2 decimales usando Decimal para evitar float."""
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def money(value) -> Decimal:
    """Convierta un valor a Decimal, aceptando str, int o float string."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def monthly_rate_from_annual_tna(annual_tna: Decimal) -> Decimal:
    """Convierte una TNA anual en porcentaje a la tasa mensual equivalente.

    Args:
        annual_tna: tasa nominal anual en porcentaje (ej. `Decimal('24.00')`).

    Returns:
        La tasa mensual equivalente (ej. `Decimal('0.02')`).

    Raises:
        InvalidAmount: si la TNA es negativa.
    """
    if annual_tna < ZERO:
        raise InvalidAmount('La TNA no puede ser negativa.')
    return annual_tna / HUNDRED / TWELVE


def french_installment(principal: Decimal, annual_tna: Decimal, months: int) -> Decimal:
    """Calcula la cuota mensual del sistema de amortización francés.

    La cuota es `P * i / (1 - (1 + i)^-n)`, con `i` la tasa mensual
    equivalente a la TNA anual. El cálculo no aplica redondeos intermedios:
    el redondeo a dos decimales ocurre una sola vez, al final.

    Args:
        principal: capital a devolver.
        annual_tna: tasa nominal anual en porcentaje.
        months: cantidad de cuotas.

    Returns:
        La cuota mensual, redondeada a dos decimales.

    Raises:
        InvalidAmount: si el principal, la tasa o los meses no son válidos.
    """
    if principal <= ZERO:
        raise InvalidAmount('El principal debe ser mayor que cero.')
    if months <= 0:
        raise InvalidAmount('La cantidad de meses debe ser mayor que cero.')
    monthly_rate = monthly_rate_from_annual_tna(annual_tna)
    if monthly_rate == ZERO:
        return round_two(principal / Decimal(months))
    discount = ONE / ((ONE + monthly_rate) ** months)
    return round_two(principal * monthly_rate / (ONE - discount))


def french_total_interest(principal: Decimal, annual_tna: Decimal, months: int) -> Decimal:
    """Calcula el interés total de un préstamo con amortización francesa.

    Args:
        principal: capital a devolver.
        annual_tna: tasa nominal anual en porcentaje.
        months: cantidad de cuotas.

    Returns:
        El interés total, redondeado a dos decimales.
    """
    installment = french_installment(
        principal=principal,
        annual_tna=annual_tna,
        months=months,
    )
    return round_two(installment * months - principal)


def french_total_cost(principal: Decimal, annual_tna: Decimal, months: int) -> Decimal:
    """Calcula el costo total de un préstamo con amortización francesa.

    Args:
        principal: capital a devolver.
        annual_tna: tasa nominal anual en porcentaje.
        months: cantidad de cuotas.

    Returns:
        El costo total (capital + interés), redondeado a dos decimales.
    """
    installment = french_installment(
        principal=principal,
        annual_tna=annual_tna,
        months=months,
    )
    return round_two(installment * months)
