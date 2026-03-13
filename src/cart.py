"""
Shopping cart logic.
"""
from typing import Dict, Optional
from .models import Product, OrderItem


class CartError(Exception):
    pass


class Cart:
    """Manages a user's shopping cart."""

    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        self._items: Dict[str, OrderItem] = {}  # product_id -> OrderItem

    def add_item(self, product: Product, quantity: int = 1) -> None:
        if quantity <= 0:
            raise CartError(f"Quantity must be positive, got {quantity}")
        if not product.is_available():
            raise CartError(f"Product '{product.name}' is out of stock")
        if product.stock < quantity:
            raise CartError(
                f"Insufficient stock for '{product.name}': requested {quantity}, available {product.stock}"
            )

        if product.id in self._items:
            existing = self._items[product.id]
            new_qty = existing.quantity + quantity
            if product.stock < new_qty:
                raise CartError(
                    f"Insufficient stock for '{product.name}': total would be {new_qty}, available {product.stock}"
                )
            self._items[product.id] = OrderItem(
                product=product,
                quantity=new_qty,
                unit_price=product.price,
            )
        else:
            self._items[product.id] = OrderItem(
                product=product,
                quantity=quantity,
                unit_price=product.price,
            )

    def remove_item(self, product_id: str) -> None:
        if product_id not in self._items:
            raise CartError(f"Product '{product_id}' not in cart")
        del self._items[product_id]

    def update_quantity(self, product_id: str, quantity: int) -> None:
        if product_id not in self._items:
            raise CartError(f"Product '{product_id}' not in cart")
        if quantity <= 0:
            self.remove_item(product_id)
            return
        item = self._items[product_id]
        if item.product.stock < quantity:
            raise CartError(
                f"Insufficient stock: requested {quantity}, available {item.product.stock}"
            )
        self._items[product_id] = OrderItem(
            product=item.product,
            quantity=quantity,
            unit_price=item.unit_price,
        )

    def get_item(self, product_id: str) -> Optional[OrderItem]:
        return self._items.get(product_id)

    def clear(self) -> None:
        self._items.clear()

    @property
    def items(self):
        return list(self._items.values())

    @property
    def total(self) -> float:
        return sum(item.subtotal for item in self._items.values())

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self._items.values())

    def is_empty(self) -> bool:
        return len(self._items) == 0

    def apply_coupon(self, code: str) -> float:
        """Returns the discount amount for a given coupon code."""
        coupons = {
            "SAVE10": 0.10,
            "SAVE20": 0.20,
            "HALFOFF": 0.50,
        }
        rate = coupons.get(code.upper())
        if rate is None:
            raise CartError(f"Invalid coupon code: '{code}'")
        return self.total * rate

    def to_dict(self) -> dict:
        return {
            "customer_id": self.customer_id,
            "items": [item.to_dict() for item in self.items],
            "total": self.total,
            "item_count": self.item_count,
        }
