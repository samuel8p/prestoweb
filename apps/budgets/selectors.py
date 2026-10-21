"""Selectores de lectura de la app budgets (interfaz pública).

Los selectores aíslan al usuario: nunca devuelven categorías ni presupuestos
de otro usuario. Además **derivan** el importe de los gastos desde el ledger:
esta app no guarda importes, solo la clasificación del usuario.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from django.db.models import QuerySet

from apps.budgets.models import Budget, Category, Expense
from apps.core.money import round_two
from apps.ledger import selectors as ledger_selectors
from apps.loans import selectors as loans_selectors

# Namespace para derivar el identificador de la alerta de un presupuesto.
ALERT_NAMESPACE = uuid.UUID('9f1c1f4e-6a2b-5c8d-9e3f-2b7a4d6c1e05')


def list_categories_for_user(user_id: uuid.UUID) -> QuerySet[Category]:
    """Lista las categorías de gasto del usuario.

    Args:
        user_id: identificador del usuario.

    Returns:
        QuerySet con las categorías del usuario ordenadas por nombre.
    """
    return Category.objects.filter(user_id=user_id).order_by('name')


def get_category_for_user(category_id: uuid.UUID, user_id: uuid.UUID) -> Category | None:
    """Devuelve la categoría del usuario, o None si no existe o es de otro.

    Args:
        category_id: identificador de la categoría.
        user_id: identificador del usuario propietario.

    Returns:
        La Category del usuario o None.
    """
    return Category.objects.filter(id=category_id, user_id=user_id).first()


def list_budgets_for_user(user_id: uuid.UUID) -> QuerySet[Budget]:
    """Lista los presupuestos del usuario.

    Args:
        user_id: identificador del usuario.

    Returns:
        QuerySet con los presupuestos del usuario.
    """
    return (
        Budget.objects.filter(user_id=user_id)
        .select_related('category')
        .order_by('category__name', 'currency')
    )


def get_budget_for_user(budget_id: uuid.UUID, user_id: uuid.UUID) -> Budget | None:
    """Devuelve el presupuesto del usuario, o None si no existe o es de otro.

    Args:
        budget_id: identificador del presupuesto.
        user_id: identificador del usuario propietario.

    Returns:
        El Budget del usuario o None.
    """
    return Budget.objects.filter(id=budget_id, user_id=user_id).select_related('category').first()


def list_expenses_for_user(
    user_id: uuid.UUID,
    category_id: uuid.UUID | None = None,
) -> QuerySet[Expense]:
    """Lista los gastos categorizados del usuario.

    Args:
        user_id: identificador del usuario.
        category_id: si se indica, solo los gastos de esa categoría.

    Returns:
        QuerySet con los gastos del usuario.
    """
    queryset = Expense.objects.filter(user_id=user_id).select_related('category')
    if category_id is not None:
        queryset = queryset.filter(category_id=category_id)
    return queryset.order_by('-created_at')


def get_expense_for_user(expense_id: uuid.UUID, user_id: uuid.UUID) -> Expense | None:
    """Devuelve el gasto del usuario, o None si no existe o es de otro.

    Args:
        expense_id: identificador del gasto.
        user_id: identificador del usuario propietario.

    Returns:
        El Expense del usuario o None.
    """
    return Expense.objects.filter(id=expense_id, user_id=user_id).select_related('category').first()


def analyze_movement_spending(
    user_id: uuid.UUID,
    transaction_ids: list[uuid.UUID],
) -> dict[uuid.UUID, dict]:
    """Analiza varios movimientos del ledger y dice cuáles son gastos del usuario.

    Por cada movimiento devuelve:

        {
            'transaction_id': UUID,
            'is_visible': bool,       # el movimiento toca alguna cuenta del usuario
            'is_expense': bool,       # el movimiento cuenta como gasto
            'amount': Decimal | None, # el importe que suma al gasto
            'currency': str | None,   # la moneda del movimiento
            'occurred_at': datetime,  # la fecha del movimiento
        }

    Los movimientos se resuelven en un lote: no hay una consulta por movimiento.

    Args:
        user_id: identificador del usuario.
        transaction_ids: identificadores de los movimientos del ledger.

    Returns:
        Dict con el análisis de cada movimiento existente, indexado por su id.
    """
    if not transaction_ids:
        return {}
    details = ledger_selectors.list_movement_details(transaction_ids=transaction_ids)
    breakdowns = loans_selectors.list_loan_movement_breakdowns(transaction_ids=list(details))
    return {
        transaction_id: _classify_movement(
            user_id=user_id,
            detail=detail,
            breakdown=breakdowns.get(transaction_id),
        )
        for transaction_id, detail in details.items()
    }


def _classify_movement(user_id: uuid.UUID, detail: dict, breakdown: dict | None) -> dict:
    """Clasifica un movimiento ya resuelto en gasto del usuario o no.

    Es una función **pura**: no consulta la base. Así las reglas defensivas se
    pueden probar sin construir movimientos imposibles con los datos reales
    (por ejemplo, una transferencia entre cuentas propias del mismo usuario:
    hoy la base no la permite porque hay una billetera por usuario y moneda).

    Reglas (decisión del cliente, HANDOFF §11.2):

    - el movimiento tiene que salir de la billetera del usuario;
    - el crédito no puede ir a otra cuenta del propio usuario;
    - el crédito no puede ir a la cuenta `system` (movimiento de inversión);
    - el desembolso de un préstamo no cuenta (el dinero se convierte en un
      activo);
    - el pago de una cuota de préstamo cuenta solo por el **interés**: el
      capital es amortización de deuda, no consumo;
    - un movimiento revertido no cuenta.

    Args:
        user_id: identificador del usuario.
        detail: detalle del movimiento, según `ledger.selectors`.
        breakdown: desglose de préstamo del movimiento, o None.

    Returns:
        El análisis del movimiento.
    """
    legs = detail['legs']
    user_legs = [leg for leg in legs if leg['account_user_id'] == user_id]
    debit = next((leg for leg in user_legs if leg['direction'] == 'debit'), None)
    credit = next(
        (leg for leg in legs if leg['direction'] == 'credit' and leg is not debit),
        None,
    )
    analysis = {
        'transaction_id': detail['transaction_id'],
        'is_visible': bool(user_legs),
        'is_expense': False,
        'amount': None,
        'currency': legs[0]['currency'] if legs else None,
        'occurred_at': detail['occurred_at'],
    }
    if detail['is_reversed'] or debit is None or credit is None:
        return analysis
    if credit['account_user_id'] == user_id:
        return analysis
    if credit['account_kind'] == 'system':
        return analysis
    if breakdown and breakdown['kind'] == 'loan_disbursement':
        return analysis
    if breakdown and breakdown['kind'] == 'installment_payment':
        amount = breakdown['interest']
    else:
        amount = debit['amount']
    if amount <= 0:
        return analysis
    analysis['is_expense'] = True
    analysis['amount'] = amount
    return analysis


def get_monthly_spending(
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    currency: str,
    year: int,
    month: int,
) -> Decimal:
    """Gasto acumulado de una categoría en un mes y una moneda.

    Solo cuentan los movimientos que el usuario categorizó, que no fueron
    revertidos y que son un gasto. El mes es el mes calendario **en UTC** y
    la moneda no se mezcla con otras: un presupuesto en ARS nunca suma gastos
    en USD.

    Args:
        user_id: identificador del usuario.
        category_id: identificador de la categoría.
        currency: moneda del presupuesto (`ARS` o `USD`).
        year: año del período.
        month: mes del período (1-12).

    Returns:
        El importe gastado en el período.
    """
    transaction_ids = list(
        Expense.objects.filter(user_id=user_id, category_id=category_id).values_list(
            'ledger_transaction_id',
            flat=True,
        )
    )
    if not transaction_ids:
        return Decimal('0.00')
    analysis = analyze_movement_spending(user_id=user_id, transaction_ids=transaction_ids)
    start, end = _month_bounds(year=year, month=month)
    total = Decimal('0.00')
    for movement in analysis.values():
        if not movement['is_expense'] or movement['currency'] != currency:
            continue
        if not start <= movement['occurred_at'] < end:
            continue
        total += movement['amount']
    return total


def list_spending_movements(
    user_id: uuid.UUID,
    category_id: uuid.UUID | None = None,
) -> list[dict]:
    """Lista los movimientos categorizados del usuario con el importe que suma.

    El importe **no** está guardado: se deriva del ledger (ver
    `analyze_movement_spending`). Los movimientos que ya no cuentan como gasto
    (revertidos, inversiones, asignaciones a un activo) quedan afuera.

    Args:
        user_id: identificador del usuario.
        category_id: si se indica, solo los gastos de esa categoría.

    Returns:
        Lista de filas con la transacción, la categoría, el importe, la moneda
        y la fecha del movimiento.
    """
    expenses = list_expenses_for_user(user_id=user_id, category_id=category_id)
    analysis = analyze_movement_spending(
        user_id=user_id,
        transaction_ids=[expense.ledger_transaction_id for expense in expenses],
    )
    rows = []
    for expense in expenses:
        movement = analysis.get(expense.ledger_transaction_id)
        if movement is None or not movement['is_expense']:
            continue
        rows.append(
            {
                'transaction_id': expense.ledger_transaction_id,
                'category_id': expense.category_id,
                'category_name': expense.category.name,
                'amount': movement['amount'],
                'currency': movement['currency'],
                'occurred_at': movement['occurred_at'],
            }
        )
    return rows


def budget_alert_reference(budget_id: uuid.UUID, year: int, month: int) -> uuid.UUID:
    """Devuelve el identificador de la alerta de un presupuesto en un mes.

    Es determinista: el mismo presupuesto en el mismo mes siempre da el mismo
    identificador, y por eso la alerta sale **una sola vez** por presupuesto y
    mes (la unicidad del aviso).

    Args:
        budget_id: identificador del presupuesto.
        year: año del período.
        month: mes del período.

    Returns:
        El identificador de la alerta.
    """
    return uuid.uuid5(ALERT_NAMESPACE, f'{budget_id}-{year}-{month}')


def find_budget_by_alert_reference(
    user_id: uuid.UUID,
    reference_id: uuid.UUID,
    year: int,
    month: int,
) -> Budget | None:
    """Devuelve el presupuesto al que corresponde un identificador de alerta.

    Args:
        user_id: identificador del usuario.
        reference_id: identificador de la alerta.
        year: año del período.
        month: mes del período.

    Returns:
        El Budget del usuario o None.
    """
    for budget in list_budgets_for_user(user_id=user_id):
        if budget_alert_reference(budget_id=budget.id, year=year, month=month) == reference_id:
            return budget
    return None


def get_budget_status(budget: Budget, year: int, month: int) -> dict:
    """Estado del presupuesto: gastado, límite, umbral, saldo y alerta.

    Args:
        budget: presupuesto del usuario.
        year: año del período.
        month: mes del período (1-12).

    Returns:
        Dict con el estado del presupuesto.
    """
    spent = get_monthly_spending(
        user_id=budget.user_id,
        category_id=budget.category_id,
        currency=budget.currency,
        year=year,
        month=month,
    )
    limit = budget.limit_amount
    threshold = round_two(limit * Decimal(budget.alert_threshold) / 100)
    return {
        'budget_id': budget.id,
        'category_id': budget.category_id,
        'period': budget.period,
        'currency': budget.currency,
        'year': year,
        'month': month,
        'limit_amount': limit,
        'spent_amount': spent,
        'remaining_amount': limit - spent,
        'threshold_amount': threshold,
        'alert_triggered': spent >= threshold,
    }


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    """Devuelve el inicio y el fin excluido del mes calendario en UTC.

    Args:
        year: año del período.
        month: mes del período (1-12).

    Returns:
        Tupla con el inicio y el fin del mes.
    """
    start = datetime(year, month, 1, tzinfo=UTC)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=UTC)
    else:
        end = datetime(year, month + 1, 1, tzinfo=UTC)
    return start, end
