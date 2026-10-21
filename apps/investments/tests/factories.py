import uuid
from datetime import date, timedelta
from decimal import Decimal

import factory

from apps.investments.models import InvestmentProduct, Position


class InvestmentProductFactory(factory.django.DjangoModelFactory):
    """Factory de InvestmentProduct."""

    class Meta:
        model = InvestmentProduct

    type = InvestmentProduct.Type.FIXED_TERM
    currency = InvestmentProduct.Currency.ARS
    term_days = 30
    annual_rate_tna = Decimal('12.00')
    min_amount = Decimal('1000.00')
    status = InvestmentProduct.Status.ACTIVE


class PositionFactory(factory.django.DjangoModelFactory):
    """Factory de Position."""

    class Meta:
        model = Position

    user_id = factory.LazyFunction(uuid.uuid4)
    product = factory.SubFactory(InvestmentProductFactory)
    amount = Decimal('5000.00')
    status = Position.Status.ACTIVE
    maturity_date = date(2026, 12, 31)
    interest_amount = Decimal('500.00')
    idempotency_key = factory.Sequence(lambda n: f'position-key-{n}')
    request_hash = factory.Sequence(lambda n: f'position-hash-{n}')


def create_approved_user(email: str = 'inversor@example.com'):
    """Crea un usuario con KYC aprobada usando los servicios de identity."""
    from apps.identity.services import register_user, resolve_kyc, submit_kyc

    user = register_user(email=email, password='TestPass123!')
    verification = submit_kyc(user=user, documents={})
    resolve_kyc(
        verification_id=verification.id,
        status='approved',
        resolved_by_user_id=uuid.uuid4(),
    )
    return user


def fund_user(user_id, amount='10000.00', currency='ARS', key='fund'):
    """Deposita fondos simulados en la billetera del usuario."""
    from apps.ledger.services import deposit

    return deposit(
        user_id=user_id,
        currency=currency,
        amount=Decimal(amount),
        idempotency_key=key,
    )


def product_with_days(term_days=30, rate='12.00', min_amount='1000.00', currency='ARS'):
    """Crea un producto de plazo fijo."""
    return InvestmentProductFactory(
        term_days=term_days,
        annual_rate_tna=Decimal(rate),
        min_amount=Decimal(min_amount),
        currency=currency,
    )


def maturity_date_for(days=30, today=None):
    """Devuelve la fecha de vencimiento de una posición abierta hoy."""
    from datetime import datetime

    from apps.investments.services import add_days

    base = today or datetime.now().date()
    return add_days(base, days)


def days_between(start: date, end: date) -> int:
    """Días corridos entre dos fechas."""
    return (end - start).days


def timedelta_days(days: int) -> timedelta:
    """Delta de días, para los tests."""
    return timedelta(days=days)
