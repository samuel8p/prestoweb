"""Vistas de la API del ledger."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import InsufficientFunds, InvalidAmount, KYCNotCompleted
from apps.core.openapi import cursor_paginated_response, paginated_response
from apps.core.pagination import StandardPagination
from apps.identity.permissions import KycApprovedForUnsafeMethods
from apps.ledger.exceptions import (
    AccountKindNotAllowed,
    AccountNotFound,
    CurrencyMismatch,
    IdempotencyConflict,
    IdempotencyKeyConflict,
    SameAccountTransfer,
    SimulatedDepositsDisabled,
)
from apps.ledger.models import Account, LedgerTransaction
from apps.ledger.selectors import (
    get_balance,
    get_transaction,
    list_accounts_for_user,
    list_transactions_for_user,
)
from apps.ledger.serializers import (
    AccountSerializer,
    BalanceSerializer,
    CreateAccountSerializer,
    CreateTransactionSerializer,
    LedgerTransactionSerializer,
)
from apps.ledger.services import create_user_wallet, deposit, transfer, withdraw


class TransactionCursorPagination(CursorPagination):
    """Paginación por cursor para los movimientos del libro mayor (AGENTS §8)."""

    page_size = 50
    max_page_size = 200
    ordering = ('-occurred_at', '-id')


def create_transaction(request, data, idempotency_key):
    """Crea el movimiento pedido y traduce los errores de dominio a HTTP.

    El tipo de movimiento ya viene validado por el serializer: solo admite
    `deposit`, `withdrawal` y `transfer`.
    """
    try:
        if data['type'] == LedgerTransaction.Type.DEPOSIT:
            return deposit(
                user_id=request.user.id,
                currency=data['currency'],
                amount=data['amount'],
                idempotency_key=idempotency_key,
                description=data.get('description', ''),
            )
        if data['type'] == LedgerTransaction.Type.WITHDRAWAL:
            return withdraw(
                user_id=request.user.id,
                currency=data['currency'],
                amount=data['amount'],
                idempotency_key=idempotency_key,
                description=data.get('description', ''),
            )
        destination_account_id = data.get('destination_account_id')
        if destination_account_id is None:
            raise ValidationError(
                {'destination_account_id': ['Es obligatorio para transferencias.']}
            )
        source = list_accounts_for_user(user_id=request.user.id).filter(
            currency=data['currency'],
            kind=Account.Kind.USER_WALLET,
        )
        if not source.exists():
            raise AccountNotFound('No tenés una billetera en esa moneda.')
        return transfer(
            user_id=request.user.id,
            source_account_id=source.first().id,
            destination_account_id=destination_account_id,
            amount=data['amount'],
            idempotency_key=idempotency_key,
            description=data.get('description', ''),
        )
    except IdempotencyConflict as exc:
        raise IdempotencyKeyConflict() from exc
    except KYCNotCompleted as exc:
        raise PermissionDenied(str(exc)) from exc
    except InsufficientFunds as exc:
        raise ValidationError({'amount': [str(exc)]}) from exc
    except InvalidAmount as exc:
        raise ValidationError({'amount': [str(exc)]}) from exc
    except SimulatedDepositsDisabled as exc:
        raise ValidationError({'type': [str(exc)]}) from exc
    except (AccountNotFound, AccountKindNotAllowed, CurrencyMismatch, SameAccountTransfer) as exc:
        raise ValidationError({'detail': [str(exc)]}) from exc


class AccountListCreateView(APIView):
    """Cuentas del usuario autenticado."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        responses={200: paginated_response(AccountSerializer)},
        summary='Listar las cuentas del usuario',
    )
    def get(self, request):
        """Lista las billeteras del usuario autenticado."""
        accounts = list_accounts_for_user(user_id=request.user.id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(accounts, request, view=self)
        return paginator.get_paginated_response(AccountSerializer(page, many=True).data)

    @extend_schema(
        request=CreateAccountSerializer,
        responses={201: AccountSerializer},
        summary='Crear la billetera del usuario en una moneda',
    )
    def post(self, request):
        """Crea la billetera del usuario para la moneda indicada."""
        serializer = CreateAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = create_user_wallet(
            user_id=request.user.id,
            currency=serializer.validated_data['currency'],
        )
        return Response(AccountSerializer(account).data, status=status.HTTP_201_CREATED)


class AccountBalanceView(APIView):
    """Saldo de una cuenta propia."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: BalanceSerializer},
        summary='Ver el saldo de una cuenta propia',
    )
    def get(self, request, account_id):
        """Devuelve el saldo de la cuenta del usuario autenticado."""
        balance = get_balance(account_id=account_id, user_id=request.user.id)
        if balance is None:
            raise NotFound('La cuenta solicitada no existe.')
        account = list_accounts_for_user(user_id=request.user.id).filter(id=account_id).first()
        return Response(
            BalanceSerializer(
                {
                    'account_id': account_id,
                    'currency': account.currency,
                    'balance': balance,
                }
            ).data,
            status=status.HTTP_200_OK,
        )


class TransactionListCreateView(KycApprovedForUnsafeMethods, APIView):
    """Movimientos del libro mayor del usuario autenticado."""

    permission_classes = [IsAuthenticated]
    pagination_class = TransactionCursorPagination

    @extend_schema(
        responses={200: cursor_paginated_response(LedgerTransactionSerializer)},
        summary='Listar los movimientos del usuario',
        operation_id='ledger_transactions_list',
    )
    def get(self, request):
        """Lista los movimientos creados por el usuario autenticado."""
        transactions = list_transactions_for_user(user_id=request.user.id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(transactions, request, view=self)
        return paginator.get_paginated_response(LedgerTransactionSerializer(page, many=True).data)

    @extend_schema(
        request=CreateTransactionSerializer,
        responses={201: LedgerTransactionSerializer},
        summary='Crear un movimiento de dinero',
    )
    def post(self, request):
        """Crea un depósito, retiro o transferencia con idempotencia."""
        serializer = CreateTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            raise ValidationError(
                {'idempotency_key': ['El header Idempotency-Key es obligatorio.']}
            )
        ledger_transaction = create_transaction(
            request,
            serializer.validated_data,
            idempotency_key,
        )
        return Response(
            LedgerTransactionSerializer(ledger_transaction).data,
            status=status.HTTP_201_CREATED,
        )


class TransactionDetailView(APIView):
    """Detalle de un movimiento propio."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: LedgerTransactionSerializer},
        summary='Ver un movimiento propio',
        operation_id='ledger_transactions_retrieve',
    )
    def get(self, request, transaction_id):
        """Devuelve el movimiento indicado si pertenece al usuario."""
        ledger_transaction = get_transaction(
            transaction_id=transaction_id,
            user_id=request.user.id,
        )
        if ledger_transaction is None:
            raise NotFound('La transacción solicitada no existe.')
        return Response(
            LedgerTransactionSerializer(ledger_transaction).data,
            status=status.HTTP_200_OK,
        )
