"""Tests for core.money module - pure Decimal operations."""

import pytest


def test_money_round_two():
    """Test that round_two rounds to 2 decimal places."""
    from decimal import Decimal

    from apps.core.money import round_two

    result = round_two(Decimal('10.555'))
    assert result == Decimal('10.56')


def test_money_money():
    """Test that money function returns Decimal."""
    from decimal import Decimal

    from apps.core.money import money

    result = money('10.50')
    assert result == Decimal('10.50')


def test_money_zero():
    """Test money with zero."""
    from decimal import Decimal

    from apps.core.money import money

    result = money('0')
    assert result == Decimal('0')


def test_monthly_rate_from_annual_tna():
    """La TNA anual en % se convierte a la tasa mensual equivalente."""
    from decimal import Decimal

    from apps.core.money import monthly_rate_from_annual_tna

    assert monthly_rate_from_annual_tna(Decimal('24.00')) == Decimal('0.02')
    assert monthly_rate_from_annual_tna(Decimal('0.00')) == Decimal('0')


def test_french_installment_without_interest():
    """Sin interés la cuota es el principal dividido en los meses."""
    from decimal import Decimal

    from apps.core.money import french_installment

    installment = french_installment(
        principal=Decimal('1000.00'),
        annual_tna=Decimal('0'),
        months=12,
    )

    assert installment == Decimal('83.33')


def test_french_installment_with_annual_tna():
    """La cuota mensual francesa de 10.000 a 24% TNA a 12 meses."""
    from decimal import Decimal

    from apps.core.money import french_installment

    installment = french_installment(
        principal=Decimal('10000.00'),
        annual_tna=Decimal('24.00'),
        months=12,
    )

    assert installment == Decimal('945.60')


def test_french_installment_decreases_with_more_months():
    """A más meses, la cuota mensual es menor."""
    from decimal import Decimal

    from apps.core.money import french_installment

    short = french_installment(
        principal=Decimal('10000.00'),
        annual_tna=Decimal('24.00'),
        months=6,
    )
    long = french_installment(
        principal=Decimal('10000.00'),
        annual_tna=Decimal('24.00'),
        months=24,
    )

    assert long < short


def test_french_total_interest_and_cost():
    """El interés total es la diferencia entre el costo total y el principal."""
    from decimal import Decimal

    from apps.core.money import french_total_cost, french_total_interest

    total_interest = french_total_interest(
        principal=Decimal('10000.00'),
        annual_tna=Decimal('24.00'),
        months=12,
    )
    total_cost = french_total_cost(
        principal=Decimal('10000.00'),
        annual_tna=Decimal('24.00'),
        months=12,
    )

    assert total_interest == Decimal('1347.20')
    assert total_cost == Decimal('11347.20')
    assert total_cost - total_interest == Decimal('10000.00')


def test_french_installment_rejects_invalid_amounts():
    """Un principal, una tasa o una cantidad de meses inválidos se rechazan."""
    from decimal import Decimal

    from apps.core.exceptions import InvalidAmount
    from apps.core.money import french_installment

    with pytest.raises(InvalidAmount):
        french_installment(
            principal=Decimal('0.00'),
            annual_tna=Decimal('24.00'),
            months=12,
        )

    with pytest.raises(InvalidAmount):
        french_installment(
            principal=Decimal('1000.00'),
            annual_tna=Decimal('24.00'),
            months=0,
        )

    with pytest.raises(InvalidAmount):
        french_installment(
            principal=Decimal('1000.00'),
            annual_tna=Decimal('-1.00'),
            months=12,
        )
