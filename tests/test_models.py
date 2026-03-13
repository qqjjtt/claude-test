"""
Tests for src/models.py

Coverage gaps:
  - Order.ship() — not tested
  - Order.cancel() on a non-cancellable status — not tested
  - Address.__str__ with and without state — partially tested
  - Product.apply_discount() edge cases (0%, 100%, out-of-range) — missing
  - Order.to_dict() — not tested
"""
import pytest
from datetime import datetime
from src.models import (
    Address, Product, OrderItem, Order, OrderStatus
)


# ---------------------------------------------------------------------------
# Address
# ---------------------------------------------------------------------------

class TestAddress:
    def test_to_dict(self):
        addr = Address(street="1 Main St", city="Springfield", country="US", postal_code="12345")
        d = addr.to_dict()
        assert d["street"] == "1 Main St"
        assert d["city"] == "Springfield"
        assert d["country"] == "US"
        assert d["postal_code"] == "12345"
        assert d["state"] is None

    def test_from_dict(self):
        data = {
            "street": "1 Main St",
            "city": "Springfield",
            "country": "US",
            "postal_code": "12345",
            "state": "IL",
        }
        addr = Address.from_dict(data)
        assert addr.state == "IL"
        assert addr.city == "Springfield"

    def test_str_without_state(self):
        addr = Address(street="1 Main St", city="Springfield", country="US", postal_code="12345")
        assert str(addr) == "1 Main St, Springfield, 12345, US"

    # MISSING: test_str_with_state


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class TestProduct:
    def _make_product(self, stock=10):
        return Product(id="p1", name="Widget", price=9.99, stock=stock, category="gadgets")

    def test_is_available_when_in_stock(self):
        p = self._make_product(stock=5)
        assert p.is_available() is True

    def test_is_available_when_out_of_stock(self):
        p = self._make_product(stock=0)
        assert p.is_available() is False

    def test_apply_discount_basic(self):
        p = self._make_product()
        discounted = p.apply_discount(10)
        assert abs(discounted - 8.991) < 0.001

    # MISSING: test_apply_discount_zero_percent
    # MISSING: test_apply_discount_100_percent
    # MISSING: test_apply_discount_negative_raises
    # MISSING: test_apply_discount_over_100_raises
    # MISSING: test_to_dict


# ---------------------------------------------------------------------------
# OrderItem
# ---------------------------------------------------------------------------

class TestOrderItem:
    def test_subtotal(self):
        product = Product(id="p1", name="Widget", price=5.00, stock=10, category="gadgets")
        item = OrderItem(product=product, quantity=3, unit_price=5.00)
        assert item.subtotal == 15.00


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class TestOrder:
    def _make_order(self, status=OrderStatus.PENDING):
        addr = Address(street="1 Main St", city="Springfield", country="US", postal_code="12345")
        product = Product(id="p1", name="Widget", price=10.00, stock=10, category="gadgets")
        item = OrderItem(product=product, quantity=2, unit_price=10.00)
        return Order(
            id="ord-1",
            customer_id="cust-1",
            items=[item],
            shipping_address=addr,
            status=status,
        )

    def test_total(self):
        order = self._make_order()
        assert order.total == 20.00

    def test_item_count(self):
        order = self._make_order()
        assert order.item_count == 2

    def test_can_cancel_pending(self):
        order = self._make_order(OrderStatus.PENDING)
        assert order.can_cancel() is True

    def test_can_cancel_processing(self):
        order = self._make_order(OrderStatus.PROCESSING)
        assert order.can_cancel() is True

    def test_can_cancel_shipped(self):
        order = self._make_order(OrderStatus.SHIPPED)
        assert order.can_cancel() is False

    def test_cancel_pending_order(self):
        order = self._make_order(OrderStatus.PENDING)
        order.cancel()
        assert order.status == OrderStatus.CANCELLED

    def test_cancel_delivered_raises(self):
        order = self._make_order(OrderStatus.DELIVERED)
        with pytest.raises(ValueError, match="Cannot cancel"):
            order.cancel()

    # MISSING: test_ship_from_processing_succeeds
    # MISSING: test_ship_from_pending_raises
    # MISSING: test_ship_from_shipped_raises
    # MISSING: test_to_dict
