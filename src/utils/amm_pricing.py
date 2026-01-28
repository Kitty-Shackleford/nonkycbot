"""AMM (Automated Market Maker) pricing calculations for liquidity pools."""

from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple


class PoolReserves(NamedTuple):
    """Liquidity pool reserve amounts for constant product AMM."""

    reserve_token_a: Decimal
    reserve_token_b: Decimal
    token_a_symbol: str
    token_b_symbol: str


class SwapQuote(NamedTuple):
    """Quote for a swap execution in an AMM pool."""

    amount_in: Decimal
    amount_out: Decimal
    effective_price: Decimal
    price_impact: Decimal  # Percentage
    fee_amount: Decimal


def calculate_constant_product_output(
    amount_in: Decimal,
    reserve_in: Decimal,
    reserve_out: Decimal,
    fee_rate: Decimal = Decimal("0.003"),  # 0.3% default
) -> Decimal:
    """
    Calculate output amount for constant product AMM (x * y = k formula).

    Used by Uniswap V2, SushiSwap, PancakeSwap and similar AMMs.

    Args:
        amount_in: Amount of input token
        reserve_in: Reserve of input token in pool
        reserve_out: Reserve of output token in pool
        fee_rate: Fee percentage as decimal (0.003 = 0.3%)

    Returns:
        Amount of output token received

    Formula:
        amount_in_with_fee = amount_in * (1 - fee_rate)
        amount_out = (amount_in_with_fee * reserve_out) / (reserve_in + amount_in_with_fee)
    """
    if amount_in <= 0:
        return Decimal("0")

    if reserve_in <= 0 or reserve_out <= 0:
        raise ValueError("Pool reserves must be positive")

    amount_in_with_fee = amount_in * (Decimal("1") - fee_rate)
    numerator = amount_in_with_fee * reserve_out
    denominator = reserve_in + amount_in_with_fee

    return numerator / denominator


def calculate_constant_product_input(
    amount_out: Decimal,
    reserve_in: Decimal,
    reserve_out: Decimal,
    fee_rate: Decimal = Decimal("0.003"),
) -> Decimal:
    """
    Calculate required input amount to receive exact output amount.

    Inverse of calculate_constant_product_output.

    Args:
        amount_out: Desired amount of output token
        reserve_in: Reserve of input token in pool
        reserve_out: Reserve of output token in pool
        fee_rate: Fee percentage as decimal

    Returns:
        Required amount of input token

    Formula:
        amount_in = (reserve_in * amount_out) / ((reserve_out - amount_out) * (1 - fee_rate))
    """
    if amount_out <= 0:
        return Decimal("0")

    if amount_out >= reserve_out:
        raise ValueError("Cannot swap more than pool reserve")

    if reserve_in <= 0 or reserve_out <= 0:
        raise ValueError("Pool reserves must be positive")

    numerator = reserve_in * amount_out
    denominator = (reserve_out - amount_out) * (Decimal("1") - fee_rate)

    return numerator / denominator


def get_swap_quote(
    amount_in: Decimal,
    reserves: PoolReserves,
    token_in: str,
    fee_rate: Decimal = Decimal("0.003"),
) -> SwapQuote:
    """
    Get a complete quote for swapping tokens in an AMM pool.

    Args:
        amount_in: Amount of input token
        reserves: Current pool reserves
        token_in: Symbol of token being swapped in
        fee_rate: Fee percentage as decimal

    Returns:
        SwapQuote with amount out, effective price, and price impact
    """
    # Determine which direction we're swapping
    if token_in == reserves.token_a_symbol:
        reserve_in = reserves.reserve_token_a
        reserve_out = reserves.reserve_token_b
    elif token_in == reserves.token_b_symbol:
        reserve_in = reserves.reserve_token_b
        reserve_out = reserves.reserve_token_a
    else:
        raise ValueError(
            f"Token {token_in} not found in pool "
            f"({reserves.token_a_symbol}/{reserves.token_b_symbol})"
        )

    # Calculate output amount with slippage
    amount_out = calculate_constant_product_output(
        amount_in, reserve_in, reserve_out, fee_rate
    )

    # Calculate effective price (how much output per unit input)
    effective_price = amount_out / amount_in if amount_in > 0 else Decimal("0")

    # Calculate spot price (price with zero slippage)
    spot_price = reserve_out / reserve_in

    # Calculate price impact (difference from spot price)
    if spot_price > 0:
        price_impact = abs(effective_price - spot_price) / spot_price * Decimal("100")
    else:
        price_impact = Decimal("0")

    # Calculate fee amount
    fee_amount = amount_in * fee_rate

    return SwapQuote(
        amount_in=amount_in,
        amount_out=amount_out,
        effective_price=effective_price,
        price_impact=price_impact,
        fee_amount=fee_amount,
    )


def calculate_minimum_received(
    amount_out: Decimal, slippage_tolerance: Decimal = Decimal("0.01")
) -> Decimal:
    """
    Calculate minimum amount to receive accounting for additional slippage tolerance.

    Args:
        amount_out: Expected output amount
        slippage_tolerance: Maximum acceptable slippage (0.01 = 1%)

    Returns:
        Minimum amount that must be received for trade to succeed
    """
    return amount_out * (Decimal("1") - slippage_tolerance)


def estimate_optimal_trade_size(
    reserves: PoolReserves,
    max_price_impact: Decimal = Decimal("0.01"),  # 1% max impact
    fee_rate: Decimal = Decimal("0.003"),
) -> dict[str, Decimal]:
    """
    Estimate optimal trade size to stay under max price impact.

    For constant product AMM, price impact increases with trade size.
    This calculates the maximum trade size for a given price impact threshold.

    Args:
        reserves: Current pool reserves
        max_price_impact: Maximum acceptable price impact (0.01 = 1%)
        fee_rate: Fee percentage as decimal

    Returns:
        Dictionary with optimal trade sizes for both directions
    """
    # For constant product AMM, price impact ≈ amount_in / reserve_in for
    # small trades.  So max trade ≈ max_price_impact * reserve.
    # max_price_impact is already a fraction (0.01 = 1%), not a percentage.
    optimal_a_to_b = reserves.reserve_token_a * max_price_impact
    optimal_b_to_a = reserves.reserve_token_b * max_price_impact

    return {
        f"{reserves.token_a_symbol}_to_{reserves.token_b_symbol}": optimal_a_to_b,
        f"{reserves.token_b_symbol}_to_{reserves.token_a_symbol}": optimal_b_to_a,
    }


def calculate_pool_spot_price(reserves: PoolReserves, quote_token: str) -> Decimal:
    """
    Calculate the spot price (price with zero slippage) of a token in the pool.

    Args:
        reserves: Current pool reserves
        quote_token: Token to get price for

    Returns:
        Spot price in terms of the other token

    Example:
        If reserves = (1000 COSA, 2000 PIRATE), price of COSA in PIRATE is 2.0
    """
    if quote_token == reserves.token_a_symbol:
        # Price of token A in terms of token B
        return reserves.reserve_token_b / reserves.reserve_token_a
    elif quote_token == reserves.token_b_symbol:
        # Price of token B in terms of token A
        return reserves.reserve_token_a / reserves.reserve_token_b
    else:
        raise ValueError(
            f"Token {quote_token} not found in pool "
            f"({reserves.token_a_symbol}/{reserves.token_b_symbol})"
        )
