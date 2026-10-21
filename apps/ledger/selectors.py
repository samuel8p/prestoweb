"""Selectores de lectura de la app ledger (interfaz pública)."""

import uuid
from decimal import Decimal

from django.db.models import QuerySet

from apps.ledger.models import Account, LedgerTransaction


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
    """Lista las transacciones creadas por el usuario, de la más reciente a la más antigua.

    Args:
        user_id: identificador del usuario.

    Returns:
        QuerySet con las transacciones del usuario.
    """
    return (
        LedgerTransaction.objects.filter(created_by_user_id=user_id)
        .prefetch_related('entries__account')
        .order_by('-occurred_at', '-id')
    )


def get_transaction(transaction_id: uuid.UUID, user_id: uuid.UUID) -> LedgerTransaction | None:
    """Devuelve la transacción del usuario, o None si no existe o es de otro.

    Args:
        transaction_id: identificador de la transacción.
        user_id: identificador del usuario creador.

    Returns:
        La LedgerTransaction o None.
    """
    return LedgerTransaction.objects.filter(id=transaction_id, created_by_user_id=user_id).first()


def get_counterpart_account(kind: str, currency: str) -> Account:
    """Devuelve la cuenta de contrapartida de un tipo y moneda, creándola si falta.

    Args:
        kind: `custody` o `system`.
        currency: código ISO de la moneda.

    Returns:
        La Account de contrapartida.
    """
    account, _ = Account.objects.get_or_create(
        user_id=None,
        kind=kind,
        currency=currency,
        defaults={'balance': Decimal('0.00')},
    )
    return account
