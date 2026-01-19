"""Tests for AMM pricing calculations."""

from decimal import Decimal

import pytest

from utils.amm_pricing import (
    PoolReserves,
    SwapQuote,
    calculate_constant_product_input,
    calculate_constant_product_output,
    calculate_pool_spot_price,
    estimate_optimal_trade_size,
    get_swap_quote,
)


def test_constant_product_output_basic():
    """Test basic constant product AMM output calculation."""
    # Pool: 1000 TokenA, 2000 TokenB
    # Swap 100 TokenA → ? TokenB
    # Expected: ~181.6 TokenB (with 0.3% fee)
    amount_in = Decimal("100")
    reserve_in = Decimal("1000")
    reserve_out = Decimal("2000")
    fee_rate = Decimal("0.003")

    output = calculate_constant_product_output(
        amount_in, reserve_in, reserve_out, fee_rate
    )

    # Manual calculation:
    # amount_with_fee = 100 * 0.997 = 99.7
    # output = (99.7 * 2000) / (1000 + 99.7) = 199400 / 1099.7 ≈ 181.322
    expected = Decimal("181.322")
    assert abs(output - expected) < Decimal(
        "0.01"
    ), f"Expected ~{expected}, got {output}"


def test_constant_product_output_no_fee():
    """Test constant product output without fees."""
    amount_in = Decimal("100")
    reserve_in = Decimal("1000")
    reserve_out = Decimal("2000")
    fee_rate = Decimal("0")

    output = calculate_constant_product_output(
        amount_in, reserve_in, reserve_out, fee_rate
    )

    # Without fee: (100 * 2000) / (1000 + 100) = 200000 / 1100 ≈ 181.818
    expected = Decimal("181.818")
    assert abs(output - expected) < Decimal("0.01")


def test_constant_product_output_zero_input():
    """Test with zero input amount."""
    output = calculate_constant_product_output(
        Decimal("0"), Decimal("1000"), Decimal("2000")
    )
    assert output == Decimal("0")


def test_constant_product_output_negative_input():
    """Test with negative input amount."""
    output = calculate_constant_product_output(
        Decimal("-10"), Decimal("1000"), Decimal("2000")
    )
    assert output == Decimal("0")


def test_constant_product_output_invalid_reserves():
    """Test with invalid reserve amounts."""
    with pytest.raises(ValueError, match="reserves must be positive"):
        calculate_constant_product_output(Decimal("100"), Decimal("0"), Decimal("2000"))

    with pytest.raises(ValueError, match="reserves must be positive"):
        calculate_constant_product_output(
            Decimal("100"), Decimal("1000"), Decimal("-2000")
        )


def test_constant_product_input_basic():
    """Test calculating required input for desired output."""
    # Want 100 TokenB from pool (1000 TokenA, 2000 TokenB)
    amount_out = Decimal("100")
    reserve_in = Decimal("1000")
    reserve_out = Decimal("2000")
    fee_rate = Decimal("0.003")

    input_needed = calculate_constant_product_input(
        amount_out, reserve_in, reserve_out, fee_rate
    )

    # Verify by running output calculation
    actual_output = calculate_constant_product_output(
        input_needed, reserve_in, reserve_out, fee_rate
    )

    # Should get approximately the desired output (within rounding)
    assert abs(actual_output - amount_out) < Decimal("0.01")


def test_constant_product_input_excessive_output():
    """Test when requested output exceeds reserves."""
    with pytest.raises(ValueError, match="Cannot swap more than pool reserve"):
        calculate_constant_product_input(
            Decimal("2001"),  # More than reserve_out
            Decimal("1000"),
            Decimal("2000"),
        )


def test_get_swap_quote():
    """Test complete swap quote calculation."""
    reserves = PoolReserves(
        reserve_token_a=Decimal("1000"),
        reserve_token_b=Decimal("2000"),
        token_a_symbol="COSA",
        token_b_symbol="PIRATE",
    )

    # Swap 100 COSA → PIRATE
    quote = get_swap_quote(
        amount_in=Decimal("100"),
        reserves=reserves,
        token_in="COSA",
        fee_rate=Decimal("0.003"),
    )

    # Verify quote structure
    assert isinstance(quote, SwapQuote)
    assert quote.amount_in == Decimal("100")
    assert quote.amount_out > 0
    assert quote.effective_price > 0
    assert quote.price_impact >= 0
    assert quote.fee_amount == Decimal("100") * Decimal("0.003")

    # Effective price should be less than spot price due to slippage
    spot_price = calculate_pool_spot_price(reserves, "COSA")
    assert quote.effective_price < spot_price


def test_get_swap_quote_invalid_token():
    """Test swap quote with invalid token."""
    reserves = PoolReserves(
        reserve_token_a=Decimal("1000"),
        reserve_token_b=Decimal("2000"),
        token_a_symbol="COSA",
        token_b_symbol="PIRATE",
    )

    with pytest.raises(ValueError, match="Token.*not found"):
        get_swap_quote(
            amount_in=Decimal("100"),
            reserves=reserves,
            token_in="BTC",  # Not in pool
        )


def test_calculate_pool_spot_price():
    """Test spot price calculation."""
    reserves = PoolReserves(
        reserve_token_a=Decimal("1000"),
        reserve_token_b=Decimal("2000"),
        token_a_symbol="COSA",
        token_b_symbol="PIRATE",
    )

    # Price of COSA in terms of PIRATE
    price_cosa = calculate_pool_spot_price(reserves, "COSA")
    assert price_cosa == Decimal("2")  # 2000 PIRATE / 1000 COSA = 2 PIRATE per COSA

    # Price of PIRATE in terms of COSA
    price_pirate = calculate_pool_spot_price(reserves, "PIRATE")
    assert price_pirate == Decimal(
        "0.5"
    )  # 1000 COSA / 2000 PIRATE = 0.5 COSA per PIRATE


def test_estimate_optimal_trade_size():
    """Test optimal trade size estimation."""
    reserves = PoolReserves(
        reserve_token_a=Decimal("10000"),
        reserve_token_b=Decimal("5000"),
        token_a_symbol="COSA",
        token_b_symbol="PIRATE",
    )

    optimal = estimate_optimal_trade_size(
        reserves=reserves,
        max_price_impact=Decimal("1.0"),  # 1% max impact
    )

    # Should return trade sizes for both directions
    assert "COSA_to_PIRATE" in optimal
    assert "PIRATE_to_COSA" in optimal

    # Trade sizes should be positive and reasonable
    assert optimal["COSA_to_PIRATE"] > 0
    assert optimal["PIRATE_to_COSA"] > 0

    # Should be small fraction of reserves for low price impact
    assert optimal["COSA_to_PIRATE"] < reserves.reserve_token_a * Decimal("0.1")
    assert optimal["PIRATE_to_COSA"] < reserves.reserve_token_b * Decimal("0.1")


def test_large_trade_slippage():
    """Test that larger trades have more slippage."""
    reserves = PoolReserves(
        reserve_token_a=Decimal("1000"),
        reserve_token_b=Decimal("1000"),
        token_a_symbol="COSA",
        token_b_symbol="PIRATE",
    )

    # Small trade
    quote_small = get_swap_quote(
        amount_in=Decimal("10"),
        reserves=reserves,
        token_in="COSA",
    )

    # Large trade
    quote_large = get_swap_quote(
        amount_in=Decimal("100"),
        reserves=reserves,
        token_in="COSA",
    )

    # Large trade should have:
    # 1. Higher price impact
    # 2. Worse effective price (lower output per input)
    assert quote_large.price_impact > quote_small.price_impact
    assert quote_large.effective_price < quote_small.effective_price


def test_roundtrip_consistency():
    """Test that swapping back and forth loses money (fees + slippage)."""
    reserves = PoolReserves(
        reserve_token_a=Decimal("1000"),
        reserve_token_b=Decimal("1000"),
        token_a_symbol="COSA",
        token_b_symbol="PIRATE",
    )

    # Swap 100 COSA → PIRATE
    quote1 = get_swap_quote(
        amount_in=Decimal("100"),
        reserves=reserves,
        token_in="COSA",
        fee_rate=Decimal("0.003"),
    )

    # Update reserves after first swap
    new_reserves = PoolReserves(
        reserve_token_a=reserves.reserve_token_a + quote1.amount_in,
        reserve_token_b=reserves.reserve_token_b - quote1.amount_out,
        token_a_symbol="COSA",
        token_b_symbol="PIRATE",
    )

    # Swap back: PIRATE → COSA
    quote2 = get_swap_quote(
        amount_in=quote1.amount_out,
        reserves=new_reserves,
        token_in="PIRATE",
        fee_rate=Decimal("0.003"),
    )

    # Should get back less than we started with
    assert quote2.amount_out < Decimal("100")

    # Loss should be approximately 2 * fee_rate (0.6%) + slippage
    # Note: Due to fee compounding and slippage interaction, loss is ~0.54-0.6%
    loss_pct = (Decimal("100") - quote2.amount_out) / Decimal("100") * 100
    assert loss_pct > Decimal("0.5")  # At least close to the fees
    assert loss_pct < Decimal("2.0")  # But not too much slippage for this size
