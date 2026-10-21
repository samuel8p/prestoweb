"""Selectores de lectura de la app budgets (interfaz pública).

Los selectores aíslan al usuario: nunca devuelven categorías ni presupuestos
de otro usuario. Además **derivan** el importe de los gastos desde el ledger:
esta app no guarda importes, solo la clasificación del usuario.
"""

import uuid
from decimal import Decimal

from django.db.models import QuerySet

from apps.budgets.models import Budget, Category, Expense
from apps.ledger import selectors as ledger_selectors
from apps.loans import selectors as loans_selectors


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
