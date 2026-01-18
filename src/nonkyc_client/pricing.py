"""Pricing and notional helpers."""

from decimal import Decimal, ROUND_UP


def min_quantity_for_notional(
    price: Decimal, min_notional: Decimal, fee_rate: Decimal
) -> Decimal:
    """Return minimum quantity needed to meet a notional after fees."""
    price = Decimal(str(price))
    min_notional = Decimal(str(min_notional))
    fee_rate = Decimal(str(fee_rate))
    if price <= 0:
        return Decimal("0")
    denominator = price * (Decimal("1") - fee_rate)
    if denominator <= 0:
        return Decimal("0")
    return min_notional / denominator


def effective_notional(quantity: Decimal, price: Decimal, fee_rate: Decimal) -> Decimal:
    """Return notional after fees for the given quantity and price."""
    quantity = Decimal(str(quantity))
    price = Decimal(str(price))
    fee_rate = Decimal(str(fee_rate))
    return quantity * price * (Decimal("1") - fee_rate)


def round_up_to_step(quantity: Decimal, step: Decimal) -> Decimal:
    """Round quantity up to the nearest step."""
    quantity = Decimal(str(quantity))
    step = Decimal(str(step))
    if step <= 0:
        return quantity
    multiplier = (quantity / step).to_integral_value(rounding=ROUND_UP)
    return multiplier * step
