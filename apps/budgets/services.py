"""Servicios de escritura de la app budgets (interfaz pública)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from django.db import IntegrityError, transaction

from apps.budgets import selectors, signals
from apps.budgets.exceptions import (
    AlreadyCategorized,
    CategoryNotFound,
    DuplicateBudget,
    DuplicateCategory,
    InvalidBudget,
    InvalidCategory,
    MovementNotFound,
    NotAnExpense,
)
from apps.budgets.models import CATEGORY_NAME_MAX_LENGTH, Budget, Category, Expense
from apps.budgets.selectors import (
    analyze_movement_spending,
    get_category_for_user,
)


def create_category(user_id: uuid.UUID, name: str) -> Category:
    """Crea una categoría de gasto personal para el usuario.

    Args:
        user_id: identificador del usuario.
        name: nombre de la categoría.

    Returns:
        La Category creada.

    Raises:
        InvalidCategory: si el nombre está vacío o es demasiado largo.
        DuplicateCategory: si el usuario ya tiene una categoría con ese nombre.
    """
    clean_name = (name or '').strip()
    if not clean_name:
        raise InvalidCategory('El nombre de la categoría no puede estar vacío.')
    if len(clean_name) > CATEGORY_NAME_MAX_LENGTH:
        raise InvalidCategory(
            f'El nombre de la categoría no puede superar {CATEGORY_NAME_MAX_LENGTH} caracteres.'
        )
    if Category.objects.filter(user_id=user_id, name=clean_name).exists():
        raise DuplicateCategory('Ya tenés una categoría con ese nombre.')
    try:
        with transaction.atomic():
            return Category.objects.create(user_id=user_id, name=clean_name)
    except IntegrityError:
        raise DuplicateCategory('Ya tenés una categoría con ese nombre.') from None


def create_budget(
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    limit_amount: Decimal,
    currency: str,
    alert_threshold: int,
    period: str = Budget.Period.MONTHLY,
) -> Budget:
    """Crea el presupuesto de una categoría, período y moneda.

    Args:
        user_id: identificador del usuario.
        category_id: identificador de la categoría del presupuesto.
        limit_amount: límite del presupuesto, mayor que cero.
        currency: moneda del presupuesto (`ARS` o `USD`).
        alert_threshold: porcentaje del límite a partir del cual se avisa.
        period: período del presupuesto (`monthly`).

    Returns:
        El Budget creado.

    Raises:
        CategoryNotFound: si la categoría no existe o no es del usuario.
        InvalidBudget: si el límite, la moneda, el período o el umbral no son válidos.
        DuplicateBudget: si ya existe ese presupuesto.
    """
    category = get_category_for_user(category_id=category_id, user_id=user_id)
    if category is None:
        raise CategoryNotFound('La categoría no existe.')
    if not isinstance(limit_amount, Decimal):
        raise InvalidBudget('El límite del presupuesto debe ser un Decimal.')
    if limit_amount <= 0:
        raise InvalidBudget('El límite del presupuesto debe ser mayor que cero.')
    if currency not in Budget.Currency.values:
        raise InvalidBudget('La moneda del presupuesto no es válida.')
    if period not in Budget.Period.values:
        raise InvalidBudget('El período del presupuesto no es válido.')
    if not isinstance(alert_threshold, int) or not 0 <= alert_threshold <= 100:
        raise InvalidBudget('El umbral de alerta debe ser un porcentaje entre 0 y 100.')
    if Budget.objects.filter(
        user_id=user_id,
        category=category,
        period=period,
        currency=currency,
    ).exists():
        raise DuplicateBudget('Ya tenés un presupuesto para esa categoría, período y moneda.')
    try:
        with transaction.atomic():
            return Budget.objects.create(
                user_id=user_id,
                category=category,
                period=period,
                limit_amount=limit_amount,
                currency=currency,
                alert_threshold=alert_threshold,
            )
    except IntegrityError:
        raise DuplicateBudget(
            'Ya tenés un presupuesto para esa categoría, período y moneda.'
        ) from None


def categorize_movement(
    user_id: uuid.UUID,
    ledger_transaction_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Expense:
    """Categoriza un movimiento del ledger como gasto personal de una categoría.

    El gasto no guarda importe: el monto se deriva del ledger al leer. Aquí
    solo se valida que el movimiento sea un gasto del usuario y se registra
    a qué categoría pertenece.

    Args:
        user_id: identificador del usuario.
        ledger_transaction_id: identificador del movimiento del ledger.
        category_id: identificador de la categoría del gasto.

    Returns:
        El Expense creado.

    Raises:
        CategoryNotFound: si la categoría no existe o no es del usuario.
        MovementNotFound: si el movimiento no existe o no es del usuario.
        NotAnExpense: si el movimiento no cuenta como gasto.
        AlreadyCategorized: si el movimiento ya tiene categoría.
    """
    category = get_category_for_user(category_id=category_id, user_id=user_id)
    if category is None:
        raise CategoryNotFound('La categoría no existe.')
    if Expense.objects.filter(
        user_id=user_id,
        ledger_transaction_id=ledger_transaction_id,
    ).exists():
        raise AlreadyCategorized('Ese movimiento ya está categorizado.')
    analysis = analyze_movement_spending(
        user_id=user_id,
        transaction_ids=[ledger_transaction_id],
    )
    movement = analysis.get(ledger_transaction_id)
    if movement is None or not movement['is_visible']:
        raise MovementNotFound('El movimiento no existe.')
    if not movement['is_expense']:
        raise NotAnExpense('Ese movimiento no cuenta como gasto.')
    try:
        with transaction.atomic():
            expense = Expense.objects.create(
                user_id=user_id,
                category=category,
                ledger_transaction_id=ledger_transaction_id,
            )
    except IntegrityError:
        raise AlreadyCategorized('Ese movimiento ya está categorizado.') from None
    _alert_budgets(user_id=user_id, category_id=category.id)
    return expense


def _alert_budgets(user_id: uuid.UUID, category_id: uuid.UUID) -> None:
    """Emite la señal de alerta de los presupuestos de la categoría que cruzaron el umbral.

    La señal lleva un identificador derivado del presupuesto y del mes, así que
    el mismo presupuesto avisa **una sola vez por mes** (lo resuelve la
    unicidad del aviso).

    Args:
        user_id: identificador del usuario.
        category_id: categoría del gasto recién categorizado.
    """
    now = datetime.now(UTC)
    for budget in selectors.list_budgets_for_user(user_id=user_id):
        if budget.category_id != category_id:
            continue
        status = selectors.get_budget_status(budget=budget, year=now.year, month=now.month)
        if not status['alert_triggered']:
            continue
        signals.budget_alert.send(
            sender=None,
            user_id=user_id,
            reference_id=selectors.budget_alert_reference(
                budget_id=budget.id,
                year=now.year,
                month=now.month,
            ),
        )
