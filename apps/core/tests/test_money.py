"""Tests for core.money module - pure Decimal operations."""


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
