"""Helpers for checking minimum order notional."""

from decimal import Decimal


def should_skip_notional(config, symbol, side, quantity, price, order_type="limit"):
    """Return True if the order notional is below configured minimum."""
    min_notional = Decimal(str(config.get("min_notional_usd", "1.0")))
    notional = Decimal(str(quantity)) * Decimal(str(price))
    if notional < min_notional:
        print(
            "⚠️  Skipping order below min notional: "
            f"symbol={symbol} side={side} order_type={order_type} "
            f"price={price} quantity={quantity} notional={notional}"
        )
        return True
    return False
