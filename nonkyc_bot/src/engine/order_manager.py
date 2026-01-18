"""Order management scaffolding."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Order:
    order_id: str
    trading_pair: str
    side: str
    price: float
    amount: float


@dataclass
class OrderManager:
    open_orders: list[Order] = field(default_factory=list)

    def track(self, order: Order) -> None:
        self.submit(order)

    def submit(self, order: Order) -> Order:
        if self.get_open_order(order.order_id) is not None:
            raise ValueError(f"Order {order.order_id} is already tracked.")
        self.open_orders.append(order)
        return order

    def replace(self, order_id: str, new_order: Order) -> bool:
        for index, order in enumerate(self.open_orders):
            if order.order_id == order_id:
                self.open_orders[index] = new_order
                return True
        return False

    def cancel(self, order_id: str) -> bool:
        for order in list(self.open_orders):
            if order.order_id == order_id:
                self.open_orders.remove(order)
                return True
        return False

    def get_open_order(self, order_id: str) -> Order | None:
        for order in self.open_orders:
            if order.order_id == order_id:
                return order
        return None

    def list_open_orders(self) -> Iterable[Order]:
        return tuple(self.open_orders)
