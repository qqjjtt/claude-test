"""
Pricing and discount calculation logic.
"""
from typing import List, Optional
from .models import Product, Order, OrderItem


class PricingRule:
    """Base class for pricing rules."""

    def apply(self, items: List[OrderItem]) -> float:
        """Return the discount amount."""
        raise NotImplementedError


class BulkDiscountRule(PricingRule):
    """Apply a discount when quantity exceeds a threshold."""

    def __init__(self, min_quantity: int, discount_percent: float):
        if min_quantity < 2:
            raise ValueError("min_quantity must be at least 2")
        if not (0 < discount_percent <= 100):
            raise ValueError("discount_percent must be between 0 and 100")
        self.min_quantity = min_quantity
        self.discount_percent = discount_percent

    def apply(self, items: List[OrderItem]) -> float:
        discount = 0.0
        for item in items:
            if item.quantity >= self.min_quantity:
                discount += item.subtotal * (self.discount_percent / 100)
        return discount


class CategoryDiscountRule(PricingRule):
    """Apply a discount to items in a specific category."""

    def __init__(self, category: str, discount_percent: float):
        self.category = category.lower()
        self.discount_percent = discount_percent

    def apply(self, items: List[OrderItem]) -> float:
        discount = 0.0
        for item in items:
            if item.product.category.lower() == self.category:
                discount += item.subtotal * (self.discount_percent / 100)
        return discount


class FreeShippingRule:
    """Applies free shipping above a minimum order value."""

    STANDARD_SHIPPING_COST = 9.99

    def __init__(self, min_order_value: float):
        self.min_order_value = min_order_value

    def shipping_cost(self, order_total: float) -> float:
        if order_total >= self.min_order_value:
            return 0.0
        return self.STANDARD_SHIPPING_COST


class PricingEngine:
    """Applies a list of pricing rules to compute the final price."""

    def __init__(self, rules: Optional[List[PricingRule]] = None):
        self.rules = rules or []

    def add_rule(self, rule: PricingRule) -> None:
        self.rules.append(rule)

    def calculate_discount(self, items: List[OrderItem]) -> float:
        total_discount = 0.0
        for rule in self.rules:
            total_discount += rule.apply(items)
        return total_discount

    def calculate_final_price(self, items: List[OrderItem]) -> float:
        subtotal = sum(item.subtotal for item in items)
        discount = self.calculate_discount(items)
        return max(0.0, subtotal - discount)


def calculate_tax(amount: float, rate: float) -> float:
    """Calculate tax amount given a subtotal and a rate (0-1)."""
    if rate < 0 or rate > 1:
        raise ValueError(f"Tax rate must be between 0 and 1, got {rate}")
    return round(amount * rate, 2)


def format_price(amount: float, currency: str = "USD") -> str:
    """Format a price for display."""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, currency + " ")
    return f"{symbol}{amount:,.2f}"
