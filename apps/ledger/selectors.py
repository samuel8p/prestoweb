"""Selectores de lectura de la app ledger (interfaz pública)."""

import uuid
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal

from django.db.models import Exists, OuterRef, Q, QuerySet

from apps.ledger.models import Account, LedgerEntry, LedgerTransaction


def get_account_for_user(account_id: uuid.UUID, user_id: uuid.UUID) -> Account | None:
    """Devuelve la cuenta del usuario, o None si no existe o es de otro.

    Args:
        account_id: identificador de la cuenta.
        user_id: identificador del usuario propietario.

    Returns:
        La Account del usuario o None.
    """
    return Account.objects.filter(id=account_id, user_id=user_id).first()


def list_accounts_for_user(user_id: uuid.UUID) -> QuerySet[Account]:
    """Lista las billeteras del usuario.

    Args:
        user_id: identificador del usuario.

    Returns:
        QuerySet con las cuentas user_wallet del usuario.
    """
    return Account.objects.filter(user_id=user_id, kind=Account.Kind.USER_WALLET).order_by(
        'currency'
    )


def get_user_wallet(user_id: uuid.UUID, currency: str) -> Account | None:
    """Devuelve la billetera del usuario para una moneda, o None si no tiene.

    Args:
        user_id: identificador del usuario.
        currency: código ISO de la moneda.

    Returns:
        La Account user_wallet del usuario o None.
    """
    return Account.objects.filter(
        user_id=user_id,
        currency=currency,
        kind=Account.Kind.USER_WALLET,
    ).first()


def get_balance(account_id: uuid.UUID, user_id: uuid.UUID) -> Decimal | None:
    """Devuelve el saldo de la cuenta del usuario, o None si no le pertenece.

    Args:
        account_id: identificador de la cuenta.
        user_id: identificador del usuario propietario.

    Returns:
        El saldo de la cuenta o None.
    """
    account = get_account_for_user(account_id=account_id, user_id=user_id)
    if account is None:
        return None
    return account.balance


def list_transactions_for_user(user_id: uuid.UUID) -> QuerySet[LedgerTransaction]:
    """Lista los movimientos que tocan las cuentas del usuario.

    Incluye los movimientos que el usuario creó **y** los que afectaron una
    de sus cuentas (por ejemplo, una transferencia recibida).

    Args:
        user_id: identificador del usuario.

    Returns:
        QuerySet con los movimientos del usuario.
    """
    return (
        LedgerTransaction.objects.filter(
            Q(created_by_user_id=user_id) | Q(entries__account__user_id=user_id)
        )
        .distinct()
        .prefetch_related('entries__account')
        .order_by('-occurred_at', '-id')
    )


def list_user_movement_amounts(
    transactions: Iterable[LedgerTransaction],
    user_id: uuid.UUID,
) -> dict[uuid.UUID, dict[str, Decimal | str]]:
    """El importe (con signo) y la moneda de cada movimiento, para el usuario.

    El importe es el de la **pata que toca la cuenta del usuario**: un crédito
    suma (entró dinero) y un débito resta (salió dinero). La moneda es la de
    esa pata (un movimiento nunca mezcla monedas).

    Usa los asientos que el selector del listado ya precarga
    (`entries__account`): no hace ninguna consulta extra.

    Args:
        transactions: los movimientos (con los asientos precargados).
        user_id: identificador del usuario.

    Returns:
        Dict con el importe y la moneda de cada movimiento, indexado por su id.
    """
    amounts: dict[uuid.UUID, dict[str, Decimal | str]] = {}
    for transaction in transactions:
        legs = [entry for entry in transaction.entries.all() if entry.account.user_id == user_id]
        if not legs:
            continue
        total = sum(
            (
                entry.amount if entry.direction == LedgerEntry.Direction.CREDIT else -entry.amount
                for entry in legs
            ),
            Decimal('0.00'),
        )
        amounts[transaction.id] = {
            'amount': total,
            'currency': legs[0].currency,
        }
    return amounts


def list_transactions_in_period(
    user_id: uuid.UUID,
    currency: str,
    start: datetime,
    end: datetime,
) -> QuerySet[LedgerTransaction]:
    """Lista los movimientos del usuario en un rango de fechas y una moneda.

    Los movimientos son inmutables: el rango se filtra por `occurred_at`.

    Args:
        user_id: identificador del usuario.
        currency: código ISO de la moneda del movimiento.
        start: inicio del rango (inclusive).
        end: fin del rango (inclusive).

    Returns:
        QuerySet con los movimientos del usuario, del más nuevo al más viejo.
    """
    return (
        LedgerTransaction.objects.filter(
            Q(created_by_user_id=user_id) | Q(entries__account__user_id=user_id),
            entries__currency=currency,
            occurred_at__gte=start,
            occurred_at__lte=end,
        )
        .distinct()
        .prefetch_related('entries__account')
        .order_by('-occurred_at', '-id')
    )


def get_balance_breakdown(currency: str) -> dict[str, Decimal]:
    """Devuelve la suma de saldos por tipo de cuenta para una moneda.

    Es la vista pública del invariante del ledger: la suma de todos los
    saldos de una moneda es cero, y las cuentas de contrapartida (custody y
    system) compensan exactamente a las billeteras de los usuarios.

    Args:
        currency: código ISO de la moneda.

    Returns:
        Dict con las sumas por tipo de cuenta y el total.
    """
    sums = {
        Account.Kind.USER_WALLET: Decimal('0.00'),
        Account.Kind.CUSTODY: Decimal('0.00'),
        Account.Kind.SYSTEM: Decimal('0.00'),
    }
    rows = Account.objects.filter(currency=currency).values_list('kind', 'balance')
    for kind, balance in rows:
        sums[kind] = sums.get(kind, Decimal('0.00')) + balance
    return {**sums, 'total': sum(sums.values(), Decimal('0.00'))}


def get_transaction(transaction_id: uuid.UUID, user_id: uuid.UUID) -> LedgerTransaction | None:
    """Devuelve la transacción del usuario, o None si no existe o es de otro.

    Args:
        transaction_id: identificador de la transacción.
        user_id: identificador del usuario creador.

    Returns:
        La LedgerTransaction o None.
    """
    return LedgerTransaction.objects.filter(id=transaction_id, created_by_user_id=user_id).first()


def list_movement_details(transaction_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
    """Devuelve el detalle de varios movimientos resolviéndolos en un solo lote.

    El detalle de cada movimiento tiene esta forma::

        {
            'transaction_id': UUID,
            'type': str,
            'occurred_at': datetime,
            'is_reversed': bool,
            'legs': [
                {
                    'account_id': UUID,
                    'account_kind': str,
                    'account_user_id': UUID | None,
                    'direction': str,
                    'amount': Decimal,
                    'currency': str,
                },
                ...
            ],
        }

    Las patas son los asientos del movimiento: de ahí sale de qué cuenta sale el
    dinero (débito) y a qué cuenta llega (crédito). `account_user_id` es `None`
    en las cuentas de contrapartida (`custody` y `system`).

    Args:
        transaction_ids: identificadores de los movimientos a describir.

    Returns:
        Dict con el detalle de cada movimiento existente, indexado por su id.
    """
    if not transaction_ids:
        return {}
    movements = (
        LedgerTransaction.objects.filter(id__in=transaction_ids)
        .annotate(
            is_reversed=Exists(
                LedgerTransaction.objects.filter(reverses=OuterRef('pk')),
            ),
        )
        .prefetch_related('entries__account')
    )
    details = {}
    for movement in movements:
        details[movement.id] = {
            'transaction_id': movement.id,
            'type': movement.type,
            'occurred_at': movement.occurred_at,
            'is_reversed': movement.is_reversed,
            'legs': [
                {
                    'account_id': entry.account_id,
                    'account_kind': entry.account.kind,
                    'account_user_id': entry.account.user_id,
                    'direction': entry.direction,
                    'amount': entry.amount,
                    'currency': entry.currency,
                }
                for entry in movement.entries.all()
            ],
        }
    return details


def get_movement_detail(transaction_id: uuid.UUID) -> dict | None:
    """Devuelve el detalle de un movimiento, o None si no existe.

    Args:
        transaction_id: identificador del movimiento.

    Returns:
        El detalle del movimiento o None.
    """
    return list_movement_details(transaction_ids=[transaction_id]).get(transaction_id)
