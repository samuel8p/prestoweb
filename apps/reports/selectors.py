"""Selectores de lectura de la app reports (interfaz pública).

La app es **solo lectura**: no tiene modelos ni escrituras. Acá viven la
validación de los parámetros de cada reporte y las agregaciones.

Los importes son siempre de `services.py` o `selectors.py` de las apps dueñas
(AGENTS §5.2): esta app nunca importa los modelos de otra app, así que las
filas se describen con tipos propios.
"""

import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TypedDict

from django.db.models import QuerySet

from apps.budgets import selectors as budgets_selectors
from apps.investments import selectors as investments_selectors
from apps.ledger import selectors as ledger_selectors
from apps.loans import selectors as loans_selectors
from apps.reports.exceptions import InvalidReportParameters

# Monedas del proyecto (AGENTS §6: un reporte es de una sola moneda, nunca se
# mezclan ni se convierten).
CURRENCIES = ('ARS', 'USD')

# Rango máximo de un reporte, en meses calendario.
MAX_RANGE_MONTHS = 12

# Dirección de un débito en el ledger (constante de otra app: no se importa).
DEBIT = 'debit'

# Estados de una cuota y de un préstamo (constantes de otra app: no se importan).
PAID = 'paid'
ACTIVE = 'active'

# Estados de una posición de inversión (constantes de otra app).
MATURED = 'matured'


class MovementRow(TypedDict):
    """Fila del reporte de movimientos."""

    id: uuid.UUID
    type: str
    amount: Decimal
    currency: str
    occurred_at: datetime
    description: str
    is_reversed: bool


@dataclass(frozen=True)
class ReportPeriod:
    """Rango de fechas de un reporte, en UTC."""

    start_date: date
    end_date: date

    @property
    def start_datetime(self) -> datetime:
        """Inicio del rango como datetime UTC."""
        return datetime(
            self.start_date.year, self.start_date.month, self.start_date.day, tzinfo=UTC
        )

    @property
    def end_datetime(self) -> datetime:
        """Fin del rango como datetime UTC, inclusivo."""
        return datetime(
            self.end_date.year,
            self.end_date.month,
            self.end_date.day,
            23,
            59,
            59,
            999999,
            tzinfo=UTC,
        )


def parse_currency(params: Mapping[str, str]) -> str:
    """Valida la moneda del reporte.

    Args:
        params: parámetros de la query string.

    Returns:
        La moneda del reporte (`ARS` o `USD`).

    Raises:
        InvalidReportParameters: si falta o no es una moneda del proyecto.
    """
    raw = params.get('currency')
    if not raw:
        raise InvalidReportParameters('El parámetro currency es obligatorio (ARS o USD).')
    if raw not in CURRENCIES:
        raise InvalidReportParameters(f'La moneda {raw} no es válida (usá ARS o USD).')
    return raw


def parse_period(params: Mapping[str, str], today: date | None = None) -> ReportPeriod:
    """Valida el rango de fechas del reporte.

    Por defecto el reporte cubre el mes calendario actual en UTC. El rango no
    puede cubrir más de 12 meses calendario.

    Args:
        params: parámetros de la query string.
        today: fecha de referencia para el valor por defecto.

    Returns:
        El rango del reporte.

    Raises:
        InvalidReportParameters: si las fechas no son válidas o el rango es
            mayor a 12 meses calendario.
    """
    reference = today or datetime.now(UTC).date()
    start = _parse_date(params.get('from'), 'from') or _first_day_of_month(reference)
    end = _parse_date(params.get('to'), 'to') or _last_day_of_month(reference)
    if start > end:
        raise InvalidReportParameters('El parámetro from no puede ser posterior a to.')
    if _months_inclusive(start, end) > MAX_RANGE_MONTHS:
        raise InvalidReportParameters(
            f'El rango no puede superar los {MAX_RANGE_MONTHS} meses calendario.'
        )
    return ReportPeriod(start_date=start, end_date=end)


def list_movements_for_report(
    user_id: uuid.UUID,
    currency: str,
    period: ReportPeriod,
) -> QuerySet:
    """Lista los movimientos del usuario en el rango y la moneda del reporte.

    Args:
        user_id: identificador del usuario.
        currency: moneda del reporte.
        period: rango de fechas del reporte.

    Returns:
        QuerySet con los movimientos, del más nuevo al más viejo.
    """
    return ledger_selectors.list_transactions_in_period(
        user_id=user_id,
        currency=currency,
        start=period.start_datetime,
        end=period.end_datetime,
    )


def build_movement_rows(transactions: Iterable) -> list[MovementRow]:
    """Arma las filas del reporte de movimientos.

    El importe es el total del movimiento (la suma de los débitos) y
    `is_reversed` dice si el movimiento fue revertido por un staff.

    Args:
        transactions: movimientos a describir.

    Returns:
        Lista de filas del reporte.
    """
    transactions = list(transactions)
    details = ledger_selectors.list_movement_details(
        transaction_ids=[transaction.id for transaction in transactions]
    )
    rows = []
    for transaction in transactions:
        detail = details.get(transaction.id)
        if detail is None:
            continue
        legs = detail['legs']
        if not legs:
            continue
        amount = sum(
            (leg['amount'] for leg in legs if leg['direction'] == DEBIT),
            Decimal('0.00'),
        )
        rows.append(
            MovementRow(
                id=transaction.id,
                type=transaction.type,
                amount=amount,
                currency=legs[0]['currency'],
                occurred_at=transaction.occurred_at,
                description=transaction.description,
                is_reversed=detail['is_reversed'],
            )
        )
    return rows


def get_spending_report(user_id: uuid.UUID, currency: str, period: ReportPeriod) -> dict:
    """Gasto acumulado por categoría en el rango y la moneda del reporte.

    Solo cuentan los movimientos que el usuario categorizó: los que no tienen
    categoría no se asignan a ningún presupuesto (decisión del cliente).

    Args:
        user_id: identificador del usuario.
        currency: moneda del reporte.
        period: rango de fechas del reporte.

    Returns:
        Dict con el total, el período y las categorías con su gasto.
    """
    totals: dict[tuple[uuid.UUID, str], dict] = {}
    for movement in budgets_selectors.list_spending_movements(user_id=user_id):
        if movement['currency'] != currency:
            continue
        occurred_at = movement['occurred_at']
        if not period.start_date <= occurred_at.date() <= period.end_date:
            continue
        key = (movement['category_id'], movement['category_name'])
        entry = totals.setdefault(key, {'amount': Decimal('0.00'), 'movements': 0})
        entry['amount'] += movement['amount']
        entry['movements'] += 1
    categories = [
        {
            'category_id': category_id,
            'category_name': category_name,
            'amount': entry['amount'],
            'movements': entry['movements'],
        }
        for (category_id, category_name), entry in sorted(
            totals.items(),
            key=lambda item: (-item[1]['amount'], item[0][1]),
        )
    ]
    return {
        'currency': currency,
        'from_date': period.start_date.isoformat(),
        'to_date': period.end_date.isoformat(),
        'total': sum((category['amount'] for category in categories), Decimal('0.00')),
        'categories': categories,
    }


def get_loans_report(user_id: uuid.UUID, currency: str) -> dict:
    """Resumen de los préstamos del usuario como prestatario y como prestamista.

    `outstanding_amount` es lo que falta pagar (la suma de las cuotas
    pendientes, capital e interés) e `interest_amount` es el interés ya pagado
    (cobrado, si el usuario es el prestamista).

    Args:
        user_id: identificador del usuario.
        currency: moneda del reporte.

    Returns:
        Dict con el resumen como prestatario y como prestamista.
    """
    loans = [
        loan
        for loan in loans_selectors.list_loans_for_user(user_id=user_id)
        if loan.currency == currency
    ]
    installments = loans_selectors.list_installments_for_loans([loan.id for loan in loans])
    installments_by_loan: dict[uuid.UUID, list] = {}
    for installment in installments:
        installments_by_loan.setdefault(installment.loan_id, []).append(installment)
    return {
        'currency': currency,
        'as_borrower': _summarize_loans(
            [loan for loan in loans if loan.borrower_user_id == user_id],
            installments_by_loan,
        ),
        'as_lender': _summarize_loans(
            [loan for loan in loans if loan.lender_user_id == user_id],
            installments_by_loan,
        ),
    }


def _summarize_loans(loans: list, installments_by_loan: dict[uuid.UUID, list]) -> dict:
    """Resume un conjunto de préstamos del usuario.

    Args:
        loans: préstamos del usuario en el rol indicado.
        installments_by_loan: cuotas agrupadas por préstamo.

    Returns:
        Dict con los préstamos activos, el saldo pendiente, el interés y las
        próximas cuotas.
    """
    active_loans = 0
    outstanding = Decimal('0.00')
    interest = Decimal('0.00')
    next_installments = []
    for loan in loans:
        rows = installments_by_loan.get(loan.id, [])
        pending = [row for row in rows if row.status != PAID]
        paid = [row for row in rows if row.status == PAID]
        if loan.status == ACTIVE:
            active_loans += 1
        outstanding += sum((row.amount for row in pending), Decimal('0.00'))
        interest += sum((row.interest_amount for row in paid), Decimal('0.00'))
        if pending:
            next_installment = min(pending, key=lambda row: (row.due_date, row.number))
            next_installments.append(
                {
                    'loan_id': loan.id,
                    'number': next_installment.number,
                    'due_date': next_installment.due_date,
                    'amount': next_installment.amount,
                }
            )
    return {
        'active_loans': active_loans,
        'outstanding_amount': outstanding,
        'interest_amount': interest,
        'next_installments': sorted(next_installments, key=lambda row: row['due_date']),
    }


def get_investments_report(user_id: uuid.UUID, currency: str) -> dict:
    """Posiciones de inversión del usuario, capital invertido e interés.

    `total_invested` es el capital de las posiciones activas, `interest_expected`
    el interés que van a ganar y `interest_earned` el que ya ganaron las
    posiciones liquidadas.

    Args:
        user_id: identificador del usuario.
        currency: moneda del reporte.

    Returns:
        Dict con el resumen y las posiciones.
    """
    positions = [
        position
        for position in investments_selectors.list_positions_for_user(user_id=user_id)
        if position.product.currency == currency
    ]
    active = [position for position in positions if position.status == ACTIVE]
    matured = [position for position in positions if position.status == MATURED]
    return {
        'currency': currency,
        'total_invested': sum((position.amount for position in active), Decimal('0.00')),
        'interest_expected': sum(
            (position.interest_amount for position in active),
            Decimal('0.00'),
        ),
        'interest_earned': sum(
            (position.interest_amount for position in matured),
            Decimal('0.00'),
        ),
        'positions': [
            {
                'position_id': position.id,
                'product_id': position.product_id,
                'amount': position.amount,
                'interest_amount': position.interest_amount,
                'status': position.status,
                'opened_at': position.opened_at,
                'maturity_date': position.maturity_date,
            }
            for position in positions
        ],
    }


def build_loan_summary_rows(report: dict) -> list[dict]:
    """Filas del CSV del reporte de préstamos: una por rol.

    Args:
        report: reporte de préstamos.

    Returns:
        Lista de filas con el resumen de cada rol.
    """
    return [
        {
            'role': role,
            'active_loans': summary['active_loans'],
            'outstanding_amount': summary['outstanding_amount'],
            'interest_amount': summary['interest_amount'],
            'next_installments': len(summary['next_installments']),
        }
        for role, summary in (
            ('as_borrower', report['as_borrower']),
            ('as_lender', report['as_lender']),
        )
    ]


def _parse_date(raw: str | None, name: str) -> date | None:
    """Convierte un parámetro de fecha ISO, o None si no viene.

    Args:
        raw: valor crudo del parámetro.
        name: nombre del parámetro, para el mensaje de error.

    Returns:
        La fecha o None.

    Raises:
        InvalidReportParameters: si el valor no es una fecha ISO.
    """
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise InvalidReportParameters(f'El parámetro {name} no es una fecha ISO válida.') from exc


def _first_day_of_month(day: date) -> date:
    """Devuelve el primer día del mes de la fecha dada."""
    return day.replace(day=1)


def _last_day_of_month(day: date) -> date:
    """Devuelve el último día del mes de la fecha dada."""
    first_next = date(day.year + 1, 1, 1) if day.month == 12 else date(day.year, day.month + 1, 1)
    return first_next - timedelta(days=1)


def _months_inclusive(start: date, end: date) -> int:
    """Cantidad de meses calendario que cubre el rango, contando los dos extremos."""
    return (end.year - start.year) * 12 + (end.month - start.month) + 1
