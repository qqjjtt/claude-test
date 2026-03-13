"""
Inventory management logic.
"""
from typing import Dict, List, Optional
from .models import Product


class InventoryError(Exception):
    pass


class InventoryManager:
    """Manages product stock levels."""

    def __init__(self):
        self._products: Dict[str, Product] = {}
        self._low_stock_threshold: int = 5

    def register_product(self, product: Product) -> None:
        if product.id in self._products:
            raise InventoryError(f"Product '{product.id}' is already registered")
        self._products[product.id] = product

    def get_product(self, product_id: str) -> Optional[Product]:
        return self._products.get(product_id)

    def restock(self, product_id: str, quantity: int) -> None:
        if quantity <= 0:
            raise InventoryError(f"Restock quantity must be positive, got {quantity}")
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError(f"Unknown product '{product_id}'")
        product.stock += quantity

    def deduct_stock(self, product_id: str, quantity: int) -> None:
        if quantity <= 0:
            raise InventoryError(f"Deduct quantity must be positive, got {quantity}")
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError(f"Unknown product '{product_id}'")
        if product.stock < quantity:
            raise InventoryError(
                f"Insufficient stock for '{product_id}': have {product.stock}, need {quantity}"
            )
        product.stock -= quantity

    def low_stock_products(self) -> List[Product]:
        return [
            p for p in self._products.values()
            if p.stock <= self._low_stock_threshold
        ]

    def out_of_stock_products(self) -> List[Product]:
        return [p for p in self._products.values() if p.stock == 0]

    def set_low_stock_threshold(self, threshold: int) -> None:
        if threshold < 0:
            raise InventoryError("Threshold must be non-negative")
        self._low_stock_threshold = threshold

    def total_inventory_value(self) -> float:
        return sum(p.price * p.stock for p in self._products.values())

    def search_by_category(self, category: str) -> List[Product]:
        return [
            p for p in self._products.values()
            if p.category.lower() == category.lower()
        ]

    def search_by_tag(self, tag: str) -> List[Product]:
        return [p for p in self._products.values() if tag in p.tags]

    def all_products(self) -> List[Product]:
        return list(self._products.values())
