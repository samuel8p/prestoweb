"""Servicios de escritura de la app ledger (interfaz pública)."""

import hashlib
import json
import logging
import uuid
from collections import defaultdict
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction

from apps.core.exceptions import InsufficientFunds, InvalidAmount, KYCNotCompleted
from apps.identity.selectors import is_kyc_approved
from apps.ledger.exceptions import (
    AccountKindNotAllowed,
    AccountNotFound,
    CurrencyMismatch,
    IdempotencyConflict,
    LedgerError,
    SameAccountTransfer,
    SimulatedDepositsDisabled,
)
from apps.ledger.models import Account, LedgerEntry, LedgerTransaction

logger = logging.getLogger(__name__)


def build_request_hash(payload: dict) -> str:
    """Calcula un hash estable de un payload.

    Args:
        payload: datos de la operación.

    Returns:
        Hash SHA-256 hexadecimal del payload.
    """
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def create_user_wallet(user_id: uuid.UUID, currency: str) -> Account:
    """Crea la billetera del usuario para una moneda, si todavía no existe.

    Args:
        user_id: identificador del usuario.
        currency: código ISO de la moneda.

    Returns:
        La Account del usuario para esa moneda.
    """
    account, _ = Account.objects.get_or_create(
        user_id=user_id,
        currency=currency,
        kind=Account.Kind.USER_WALLET,
        defaults={'balance': Decimal('0.00')},
    )
    return account


def deposit(
    user_id: uuid.UUID,
    currency: str,
    amount: Decimal,
    idempotency_key: str,
    description: str = '',
) -> LedgerTransaction:
    """Deposita fondos simulados en la billetera del usuario.

    El depósito acredita la `user_wallet` y debita la cuenta de `custody`.

    Args:
        user_id: usuario que recibe el depósito.
        currency: código ISO de la moneda.
        amount: importe a acreditar, mayor que cero.
        idempotency_key: clave de idempotencia del usuario.
        description: descripción opcional del movimiento.

    Returns:
        La LedgerTransaction creada, o la original si la clave ya se usó.

    Raises:
        InvalidAmount: si el importe no es un Decimal positivo.
        KYCNotCompleted: si el usuario no tiene KYC aprobada.
        SimulatedDepositsDisabled: si los depósitos simulados están deshabilitados.
        IdempotencyConflict: si la clave ya existe con otro payload.
    """
    _assert_valid_amount(amount)
    _require_kyc(user_id)
    _require_simulated_deposits_enabled()
    request_hash = build_request_hash(
        {
            'type': LedgerTransaction.Type.DEPOSIT,
            'currency': currency,
            'amount': str(amount),
            'description': description,
        }
    )
    try:
        with transaction.atomic():
            existing = _resolve_idempotent(user_id, idempotency_key, request_hash)
            if existing is not None:
                return existing
            wallet = create_user_wallet(user_id=user_id, currency=currency)
            custody = _get_or_create_counterpart(Account.Kind.CUSTODY, currency)
            locked = _lock_accounts([wallet.id, custody.id])
            legs = [
                (locked[wallet.id], LedgerEntry.Direction.CREDIT, amount),
                (locked[custody.id], LedgerEntry.Direction.DEBIT, amount),
            ]
            return _post_transaction(
                movement_type=LedgerTransaction.Type.DEPOSIT,
                user_id=user_id,
                currency=currency,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                legs=legs,
                description=description,
            )
    except IntegrityError:
        return _recover_from_idempotency_race(user_id, idempotency_key, request_hash)


def withdraw(
    user_id: uuid.UUID,
    currency: str,
    amount: Decimal,
    idempotency_key: str,
    description: str = '',
) -> LedgerTransaction:
    """Retira fondos de la billetera del usuario.

    El retiro debita la `user_wallet` y acredita la cuenta de `custody`.

    Args:
        user_id: usuario que retira los fondos.
        currency: código ISO de la moneda.
        amount: importe a debitar, mayor que cero.
        idempotency_key: clave de idempotencia del usuario.
        description: descripción opcional del movimiento.

    Returns:
        La LedgerTransaction creada, o la original si la clave ya se usó.

    Raises:
        InvalidAmount: si el importe no es un Decimal positivo.
        KYCNotCompleted: si el usuario no tiene KYC aprobada.
        InsufficientFunds: si la billetera quedaría en negativo.
        SimulatedDepositsDisabled: si los depósitos simulados están deshabilitados.
        IdempotencyConflict: si la clave ya existe con otro payload.
    """
    _assert_valid_amount(amount)
    _require_kyc(user_id)
    _require_simulated_deposits_enabled()
    request_hash = build_request_hash(
        {
            'type': LedgerTransaction.Type.WITHDRAWAL,
            'currency': currency,
            'amount': str(amount),
            'description': description,
        }
    )
    try:
        with transaction.atomic():
            existing = _resolve_idempotent(user_id, idempotency_key, request_hash)
            if existing is not None:
                return existing
            wallet = create_user_wallet(user_id=user_id, currency=currency)
            custody = _get_or_create_counterpart(Account.Kind.CUSTODY, currency)
            locked = _lock_accounts([wallet.id, custody.id])
            _assert_sufficient_funds(locked[wallet.id], -amount)
            legs = [
                (locked[wallet.id], LedgerEntry.Direction.DEBIT, amount),
                (locked[custody.id], LedgerEntry.Direction.CREDIT, amount),
            ]
            return _post_transaction(
                movement_type=LedgerTransaction.Type.WITHDRAWAL,
                user_id=user_id,
                currency=currency,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                legs=legs,
                description=description,
            )
    except IntegrityError:
        return _recover_from_idempotency_race(user_id, idempotency_key, request_hash)


def transfer(
    user_id: uuid.UUID,
    source_account_id: uuid.UUID,
    destination_account_id: uuid.UUID,
    amount: Decimal,
    idempotency_key: str,
    description: str = '',
) -> LedgerTransaction:
    """Transfiere fondos entre dos billeteras del usuario.

    Args:
        user_id: usuario que ordena la transferencia.
        source_account_id: cuenta de origen (user_wallet del usuario).
        destination_account_id: cuenta de destino (user_wallet).
        amount: importe a mover, mayor que cero.
        idempotency_key: clave de idempotencia del usuario.
        description: descripción opcional del movimiento.

    Returns:
        La LedgerTransaction creada, o la original si la clave ya se usó.

    Raises:
        InvalidAmount: si el importe no es un Decimal positivo.
        KYCNotCompleted: si el usuario no tiene KYC aprobada.
        SameAccountTransfer: si origen y destino son la misma cuenta.
        AccountKindNotAllowed: si alguna cuenta no es una user_wallet.
        AccountNotFound: si la cuenta origen no es del usuario.
        CurrencyMismatch: si las cuentas no comparten moneda.
        InsufficientFunds: si la billetera de origen quedaría en negativo.
        IdempotencyConflict: si la clave ya existe con otro payload.
    """
    _assert_valid_amount(amount)
    _require_kyc(user_id)
    if source_account_id == destination_account_id:
        raise SameAccountTransfer('El origen y el destino no pueden ser la misma cuenta.')
    request_hash = build_request_hash(
        {
            'type': LedgerTransaction.Type.TRANSFER,
            'source_account_id': str(source_account_id),
            'destination_account_id': str(destination_account_id),
            'amount': str(amount),
            'description': description,
        }
    )
    try:
        with transaction.atomic():
            existing = _resolve_idempotent(user_id, idempotency_key, request_hash)
            if existing is not None:
                return existing
            locked = _lock_accounts([source_account_id, destination_account_id])
            source = locked[source_account_id]
            destination = locked[destination_account_id]
            if source.kind != Account.Kind.USER_WALLET:
                raise AccountKindNotAllowed('La cuenta origen debe ser una user_wallet.')
            if destination.kind != Account.Kind.USER_WALLET:
                raise AccountKindNotAllowed('La cuenta destino debe ser una user_wallet.')
            if source.user_id != user_id:
                raise AccountNotFound('La cuenta origen no pertenece al usuario.')
            if source.currency != destination.currency:
                raise CurrencyMismatch('La cuenta destino debe tener la misma moneda.')
            _assert_sufficient_funds(source, -amount)
            legs = [
                (source, LedgerEntry.Direction.DEBIT, amount),
                (destination, LedgerEntry.Direction.CREDIT, amount),
            ]
            return _post_transaction(
                movement_type=LedgerTransaction.Type.TRANSFER,
                user_id=user_id,
                currency=source.currency,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                legs=legs,
                description=description,
                destination_account_id=destination_account_id,
            )
    except IntegrityError:
        return _recover_from_idempotency_race(user_id, idempotency_key, request_hash)


def transfer_between_users(
    source_user_id: uuid.UUID,
    destination_user_id: uuid.UUID,
    currency: str,
    amount: Decimal,
    idempotency_key: str,
    initiated_by_user_id: uuid.UUID,
    description: str = '',
    movement_type: str = LedgerTransaction.Type.TRANSFER,
) -> LedgerTransaction:
    """Mueve fondos entre dos usuarios con una operación iniciada por un tercero.

    Es un service **interno**: no está expuesto por la API. Lo usan el flujo de
    préstamos y el de inversiones, donde el movimiento lo pide un tercero pero
    el saldo sale de la cuenta de otra parte. Las reglas de saldo no negativo,
    de bloqueo de cuentas en orden por `id` y de idempotencia son las mismas
    que en `transfer`.

    Args:
        source_user_id: usuario cuyo saldo se debita.
        destination_user_id: usuario cuyo saldo se acredita.
        currency: código ISO de la moneda.
        amount: importe a mover, mayor que cero.
        idempotency_key: clave de idempotencia de la operación.
        initiated_by_user_id: usuario que origina la operación.
        description: descripción del movimiento.
        movement_type: tipo de la transacción (`transfer` por defecto).

    Returns:
        La LedgerTransaction creada, o la original si la clave ya se usó.

    Raises:
        InvalidAmount: si el importe no es un Decimal positivo.
        InsufficientFunds: si la cuenta de origen quedaría en negativo.
        IdempotencyConflict: si la clave ya existe con otro payload.
    """
    _assert_valid_amount(amount)
    request_hash = build_request_hash(
        {
            'type': movement_type,
            'source_user_id': str(source_user_id),
            'destination_user_id': str(destination_user_id),
            'currency': currency,
            'amount': str(amount),
            'description': description,
        }
    )
    try:
        with transaction.atomic():
            existing = _resolve_idempotent(
                initiated_by_user_id,
                idempotency_key,
                request_hash,
            )
            if existing is not None:
                return existing
            source = create_user_wallet(user_id=source_user_id, currency=currency)
            destination = create_user_wallet(user_id=destination_user_id, currency=currency)
            locked = _lock_accounts([source.id, destination.id])
            _assert_sufficient_funds(locked[source.id], -amount)
            legs = [
                (locked[source.id], LedgerEntry.Direction.DEBIT, amount),
                (locked[destination.id], LedgerEntry.Direction.CREDIT, amount),
            ]
            return _post_transaction(
                movement_type=movement_type,
                user_id=initiated_by_user_id,
                currency=currency,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                legs=legs,
                description=description,
                destination_account_id=locked[destination.id].id,
            )
    except IntegrityError:
        return _recover_from_idempotency_race(
            initiated_by_user_id,
            idempotency_key,
            request_hash,
        )


SYSTEM_COUNTERPART = Account.Kind.SYSTEM
CUSTODY_COUNTERPART = Account.Kind.CUSTODY
INTEREST_MOVEMENT_TYPE = LedgerTransaction.Type.INTEREST


def transfer_to_counterpart(
    user_id: uuid.UUID,
    counterparty_kind: str,
    currency: str,
    amount: Decimal,
    idempotency_key: str,
    initiated_by_user_id: uuid.UUID,
    description: str = '',
    movement_type: str = LedgerTransaction.Type.TRANSFER,
) -> LedgerTransaction:
    """Mueve fondos de la billetera de un usuario a una cuenta de contrapartida.

    Es un service **interno**: la cuenta de contrapartida (`custody` o
    `system`) no tiene usuario, por eso no puede resolverse con
    `transfer_between_users`. Las reglas de saldo no negativo, de bloqueo de
    cuentas en orden por `id` y de idempotencia son las mismas.

    Args:
        user_id: usuario cuya billetera se debita.
        counterparty_kind: `custody` o `system`.
        currency: código ISO de la moneda.
        amount: importe a mover, mayor que cero.
        idempotency_key: clave de idempotencia de la operación.
        initiated_by_user_id: usuario que origina la operación.
        description: descripción del movimiento.
        movement_type: tipo de la transacción (`transfer` por defecto).

    Returns:
        La LedgerTransaction creada, o la original si la clave ya se usó.

    Raises:
        InvalidAmount: si el importe no es un Decimal positivo.
        InsufficientFunds: si la billetera quedaría en negativo.
        IdempotencyConflict: si la clave ya existe con otro payload.
    """
    return _transfer_with_counterpart(
        user_id=user_id,
        counterparty_kind=counterparty_kind,
        currency=currency,
        amount=amount,
        idempotency_key=idempotency_key,
        initiated_by_user_id=initiated_by_user_id,
        description=description,
        movement_type=movement_type,
        from_user=True,
    )


def transfer_from_counterpart(
    user_id: uuid.UUID,
    counterparty_kind: str,
    currency: str,
    amount: Decimal,
    idempotency_key: str,
    initiated_by_user_id: uuid.UUID,
    description: str = '',
    movement_type: str = LedgerTransaction.Type.TRANSFER,
) -> LedgerTransaction:
    """Mueve fondos de una cuenta de contrapartida a la billetera de un usuario.

    Es un service **interno**, hermano de `transfer_to_counterpart`.

    Args:
        user_id: usuario cuya billetera se acredita.
        counterparty_kind: `custody` o `system`.
        currency: código ISO de la moneda.
        amount: importe a mover, mayor que cero.
        idempotency_key: clave de idempotencia de la operación.
        initiated_by_user_id: usuario que origina la operación.
        description: descripción del movimiento.
        movement_type: tipo de la transacción (`transfer` por defecto).

    Returns:
        La LedgerTransaction creada, o la original si la clave ya se usó.

    Raises:
        InvalidAmount: si el importe no es un Decimal positivo.
        IdempotencyConflict: si la clave ya existe con otro payload.
    """
    return _transfer_with_counterpart(
        user_id=user_id,
        counterparty_kind=counterparty_kind,
        currency=currency,
        amount=amount,
        idempotency_key=idempotency_key,
        initiated_by_user_id=initiated_by_user_id,
        description=description,
        movement_type=movement_type,
        from_user=False,
    )


def _transfer_with_counterpart(
    *,
    user_id: uuid.UUID,
    counterparty_kind: str,
    currency: str,
    amount: Decimal,
    idempotency_key: str,
    initiated_by_user_id: uuid.UUID,
    description: str,
    movement_type: str,
    from_user: bool,
) -> LedgerTransaction:
    """Mueve saldo entre la billetera de un usuario y una cuenta de contrapartida."""
    _assert_valid_amount(amount)
    request_hash = build_request_hash(
        {
            'type': movement_type,
            'user_id': str(user_id),
            'counterparty_kind': counterparty_kind,
            'currency': currency,
            'amount': str(amount),
            'description': description,
            'direction': 'to_counterpart' if from_user else 'from_counterpart',
        }
    )
    try:
        with transaction.atomic():
            existing = _resolve_idempotent(
                initiated_by_user_id,
                idempotency_key,
                request_hash,
            )
            if existing is not None:
                return existing
            wallet = create_user_wallet(user_id=user_id, currency=currency)
            counterparty, _ = Account.objects.get_or_create(
                user_id=None,
                kind=counterparty_kind,
                currency=currency,
                defaults={'balance': Decimal('0.00')},
            )
            locked = _lock_accounts([wallet.id, counterparty.id])
            if from_user:
                _assert_sufficient_funds(locked[wallet.id], -amount)
                legs = [
                    (locked[wallet.id], LedgerEntry.Direction.DEBIT, amount),
                    (locked[counterparty.id], LedgerEntry.Direction.CREDIT, amount),
                ]
            else:
                legs = [
                    (locked[counterparty.id], LedgerEntry.Direction.DEBIT, amount),
                    (locked[wallet.id], LedgerEntry.Direction.CREDIT, amount),
                ]
            return _post_transaction(
                movement_type=movement_type,
                user_id=initiated_by_user_id,
                currency=currency,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                legs=legs,
                description=description,
            )
    except IntegrityError:
        return _recover_from_idempotency_race(
            initiated_by_user_id,
            idempotency_key,
            request_hash,
        )


def reverse_transaction(
    transaction_id: uuid.UUID,
    staff_user_id: uuid.UUID,
) -> LedgerTransaction:
    """Crea la transacción compensatoria de una transacción existente.

    Solo un usuario **staff** puede ejecutarlo y **no hay endpoint público**:
    la acción del admin de Django es la única vía de entrada.

    Args:
        transaction_id: identificador de la transacción a reversar.
        staff_user_id: identificador del usuario staff que decide.

    Returns:
        La LedgerTransaction de reversión.

    Raises:
        LedgerError: si la transacción no existe o ya fue reversada.
        InsufficientFunds: si el reverso dejaría una user_wallet en negativo.
    """
    idempotency_key = f'reversal-{transaction_id}'
    request_hash = build_request_hash(
        {'type': LedgerTransaction.Type.REVERSAL, 'transaction_id': str(transaction_id)}
    )
    with transaction.atomic():
        try:
            original = LedgerTransaction.objects.select_for_update().get(pk=transaction_id)
        except LedgerTransaction.DoesNotExist as exc:
            raise LedgerError('La transacción a reversar no existe.') from exc
        if LedgerTransaction.objects.filter(reverses=original).exists():
            raise LedgerError('La transacción ya fue reversada.')
        entries = list(original.entries.all())
        if not entries:
            raise LedgerError('La transacción no tiene asientos que revertir.')
        locked = _lock_accounts([entry.account_id for entry in entries])
        legs = []
        for entry in entries:
            account = locked[entry.account_id]
            opposite = (
                LedgerEntry.Direction.CREDIT
                if entry.direction == LedgerEntry.Direction.DEBIT
                else LedgerEntry.Direction.DEBIT
            )
            delta = entry.amount if opposite == LedgerEntry.Direction.CREDIT else -entry.amount
            _assert_sufficient_funds(account, delta)
            legs.append((account, opposite, entry.amount))
        return _post_transaction(
            movement_type=LedgerTransaction.Type.REVERSAL,
            user_id=staff_user_id,
            currency=entries[0].currency,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            legs=legs,
            description=f'Reverso de {original.id}',
            reverses=original,
        )


def _post_transaction(
    *,
    movement_type: str,
    user_id: uuid.UUID,
    currency: str,
    idempotency_key: str,
    request_hash: str,
    legs: list[tuple[Account, str, Decimal]],
    description: str = '',
    destination_account_id: uuid.UUID | None = None,
    reverses: LedgerTransaction | None = None,
) -> LedgerTransaction:
    """Crea la transacción con sus asientos y actualiza los saldos de las cuentas."""
    ledger_transaction = LedgerTransaction.objects.create(
        type=movement_type,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        created_by_user_id=user_id,
        destination_account_id=destination_account_id,
        description=description,
        reverses=reverses,
    )
    for account, direction, amount in legs:
        LedgerEntry.objects.create(
            ledger_transaction=ledger_transaction,
            account=account,
            direction=direction,
            amount=amount,
            currency=currency,
        )
    _apply_legs(legs)
    logger.info(
        'Movimiento de ledger registrado: type=%s user_id=%s transaction_id=%s',
        movement_type,
        user_id,
        ledger_transaction.id,
    )
    return ledger_transaction


def _apply_legs(legs: list[tuple[Account, str, Decimal]]) -> None:
    """Actualiza el saldo de cada cuenta con el efecto de los asientos."""
    deltas: dict[uuid.UUID, Decimal] = defaultdict(lambda: Decimal('0.00'))
    for account, direction, amount in legs:
        deltas[account.id] += amount if direction == LedgerEntry.Direction.CREDIT else -amount
    for account_id, delta in deltas.items():
        account = next(account for account, _, _ in legs if account.id == account_id)
        account.balance = account.balance + delta
        account.save(update_fields=['balance', 'updated_at'])


def _lock_accounts(account_ids: list[uuid.UUID]) -> dict[uuid.UUID, Account]:
    """Bloquea las cuentas indicadas en orden ascendente por id y las devuelve."""
    ordered_ids = sorted(account_ids)
    accounts = Account.objects.select_for_update().filter(id__in=ordered_ids).order_by('id')
    locked = {account.id: account for account in accounts}
    missing = [account_id for account_id in ordered_ids if account_id not in locked]
    if missing:
        raise AccountNotFound('La cuenta solicitada no existe.')
    return locked


def _get_or_create_counterpart(kind: str, currency: str) -> Account:
    """Devuelve la cuenta de contrapartida de un tipo y moneda, creándola si falta."""
    account, _ = Account.objects.get_or_create(
        user_id=None,
        kind=kind,
        currency=currency,
        defaults={'balance': Decimal('0.00')},
    )
    return account


def _resolve_idempotent(
    user_id: uuid.UUID,
    idempotency_key: str,
    request_hash: str,
) -> LedgerTransaction | None:
    """Devuelve la transacción original si la clave ya existe con el mismo payload.

    Raises:
        IdempotencyConflict: si la clave existe con un payload distinto.
    """
    existing = LedgerTransaction.objects.filter(
        created_by_user_id=user_id,
        idempotency_key=idempotency_key,
    ).first()
    if existing is None:
        return None
    if existing.request_hash != request_hash:
        raise IdempotencyConflict('Ya existe una operación con esa clave de idempotencia.')
    return existing


def _recover_from_idempotency_race(
    user_id: uuid.UUID,
    idempotency_key: str,
    request_hash: str,
) -> LedgerTransaction:
    """Resuelve la carrera de idempotencia devolviendo la transacción original."""
    existing = _resolve_idempotent(user_id, idempotency_key, request_hash)
    if existing is None:
        raise
    return existing


def _assert_valid_amount(amount: Decimal) -> None:
    """Verifica que el importe sea un Decimal positivo.

    Raises:
        InvalidAmount: si el importe no cumple la condición.
    """
    if not isinstance(amount, Decimal):
        raise InvalidAmount('El importe debe ser un Decimal.')
    if amount <= 0:
        raise InvalidAmount('El importe debe ser mayor que cero.')


def _assert_sufficient_funds(account: Account, delta: Decimal) -> None:
    """Verifica que el saldo resultante de la cuenta no sea negativo.

    Raises:
        InsufficientFunds: si una user_wallet quedaría en negativo.
    """
    if account.kind == Account.Kind.USER_WALLET and account.balance + delta < 0:
        raise InsufficientFunds('La cuenta no tiene saldo suficiente.')


def _require_kyc(user_id: uuid.UUID) -> None:
    """Exige KYC aprobada para operar con dinero (AGENTS §9.9).

    Raises:
        KYCNotCompleted: si el usuario no tiene KYC aprobada.
    """
    if not is_kyc_approved(user_id=user_id):
        raise KYCNotCompleted('Necesitás completar la verificación KYC para operar con dinero.')


def _require_simulated_deposits_enabled() -> None:
    """Verifica que los depósitos y retiros simulados estén habilitados.

    Raises:
        SimulatedDepositsDisabled: si la operación está deshabilitada.
    """
    if not settings.LEDGER_SIMULATED_DEPOSITS_ENABLED:
        raise SimulatedDepositsDisabled('Los depósitos simulados están deshabilitados.')
