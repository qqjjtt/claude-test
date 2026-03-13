"""
Tests for src/pricing.py

Coverage gaps:
  - CategoryDiscountRule — not tested at all
  - FreeShippingRule — not tested at all
  - PricingEngine.calculate_final_price with multiple rules — not tested
  - calculate_tax() edge cases (rate=0, rate=1, invalid rate) — mostly missing
  - format_price() with non-USD currencies and unknown currencies — not tested
"""
import pytest
from src.models import Product, OrderItem
from src.pricing import (
    BulkDiscountRule, CategoryDiscountRule, FreeShippingRule,
    PricingEngine, calculate_tax, format_price
)


def make_item(price=10.0, quantity=1, category="general", product_id="p1"):
    product = Product(id=product_id, name="Item", price=price, stock=100, category=category)
    return OrderItem(product=product, quantity=quantity, unit_price=price)


class TestBulkDiscountRule:
    def test_applies_discount_above_threshold(self):
        rule = BulkDiscountRule(min_quantity=3, discount_percent=10)
        item = make_item(price=10.0, quantity=5)
        assert rule.apply([item]) == pytest.approx(5.0)

    def test_no_discount_below_threshold(self):
        rule = BulkDiscountRule(min_quantity=3, discount_percent=10)
        item = make_item(price=10.0, quantity=2)
        assert rule.apply([item]) == 0.0

    def test_applies_at_exact_threshold(self):
        rule = BulkDiscountRule(min_quantity=3, discount_percent=10)
        item = make_item(price=10.0, quantity=3)
        assert rule.apply([item]) == pytest.approx(3.0)

    def test_invalid_min_quantity_raises(self):
        with pytest.raises(ValueError):
            BulkDiscountRule(min_quantity=1, discount_percent=10)

    def test_invalid_discount_raises(self):
        with pytest.raises(ValueError):
            BulkDiscountRule(min_quantity=3, discount_percent=0)

    # MISSING: test with multiple items where only some qualify


# MISSING: TestCategoryDiscountRule — entire class untested
# MISSING: TestFreeShippingRule — entire class untested


class TestPricingEngine:
    def test_no_rules_returns_subtotal(self):
        engine = PricingEngine()
        items = [make_item(price=10.0, quantity=2)]
        assert engine.calculate_final_price(items) == 20.0

    def test_single_rule_applies(self):
        rule = BulkDiscountRule(min_quantity=2, discount_percent=10)
        engine = PricingEngine(rules=[rule])
        items = [make_item(price=10.0, quantity=3)]
        # subtotal=30, discount=3 → 27
        assert engine.calculate_final_price(items) == pytest.approx(27.0)

    # MISSING: test_multiple_rules_stack
    # MISSING: test_discount_cannot_exceed_subtotal (floor at 0.0)
    # MISSING: test_add_rule


class TestCalculateTax:
    def test_basic_tax(self):
        assert calculate_tax(100.0, 0.1) == pytest.approx(10.0)

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError):
            calculate_tax(100.0, -0.1)

    def test_rate_above_one_raises(self):
        with pytest.raises(ValueError):
            calculate_tax(100.0, 1.1)

    # MISSING: test_rate_zero (edge case)
    # MISSING: test_rate_one (edge case)
    # MISSING: test_rounding_precision


class TestFormatPrice:
    def test_usd(self):
        assert format_price(1234.5, "USD") == "$1,234.50"

    # MISSING: test_eur
    # MISSING: test_gbp
    # MISSING: test_unknown_currency_uses_code_prefix
    # MISSING: test_zero_amount
    # MISSING: test_default_currency_is_usd
