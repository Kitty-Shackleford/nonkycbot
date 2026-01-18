"""Risk management scaffolding."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskLimits:
    min_order_size: float
    max_order_size: float
    max_exposure: float


class RiskManager:
    """Minimal risk checks placeholder."""

    def __init__(self, limits: RiskLimits) -> None:
        self.limits = limits
        self.kill_switch_triggered = False

    def trigger_kill_switch(self) -> None:
        self.kill_switch_triggered = True

    def reset_kill_switch(self) -> None:
        self.kill_switch_triggered = False

    def allows_order(self, amount: float, current_exposure: float) -> bool:
        if self.kill_switch_triggered:
            return False
        if amount < self.limits.min_order_size or amount > self.limits.max_order_size:
            return False
        projected_exposure = abs(current_exposure) + abs(amount)
        return projected_exposure <= self.limits.max_exposure
