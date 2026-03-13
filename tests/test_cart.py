"""
Tests for src/cart.py

Coverage gaps:
  - Cart.apply_coupon() — not tested at all
  - Cart.update_quantity() setting quantity to 0 (triggers remove) — not tested
  - Cart.update_quantity() exceeding stock — not tested
  - Cart.to_dict() — not tested
  - CartError on add_item with quantity <= 0 — not tested
"""
import pytest
from src.models import Product
from src.cart import Cart, CartError


def make_product(product_id="p1", name="Widget", price=9.99, stock=10):
    return Product(id=product_id, name=name, price=price, stock=stock, category="gadgets")


class TestCartAddItem:
    def test_add_single_item(self):
        cart = Cart("cust-1")
        product = make_product()
        cart.add_item(product, quantity=2)
        assert cart.item_count == 2

    def test_add_same_item_twice_accumulates(self):
        cart = Cart("cust-1")
        product = make_product()
        cart.add_item(product, quantity=1)
        cart.add_item(product, quantity=2)
        assert cart.item_count == 3

    def test_add_out_of_stock_raises(self):
        cart = Cart("cust-1")
        product = make_product(stock=0)
        with pytest.raises(CartError, match="out of stock"):
            cart.add_item(product)

    def test_add_exceeding_stock_raises(self):
        cart = Cart("cust-1")
        product = make_product(stock=3)
        with pytest.raises(CartError, match="Insufficient stock"):
            cart.add_item(product, quantity=5)

    # MISSING: test_add_item_quantity_zero_raises
    # MISSING: test_add_item_quantity_negative_raises
    # MISSING: test_add_accumulation_exceeds_stock_raises


class TestCartRemoveItem:
    def test_remove_existing_item(self):
        cart = Cart("cust-1")
        product = make_product()
        cart.add_item(product)
        cart.remove_item(product.id)
        assert cart.is_empty()

    def test_remove_missing_item_raises(self):
        cart = Cart("cust-1")
        with pytest.raises(CartError, match="not in cart"):
            cart.remove_item("nonexistent")


class TestCartUpdateQuantity:
    def test_update_quantity(self):
        cart = Cart("cust-1")
        product = make_product(stock=10)
        cart.add_item(product, quantity=2)
        cart.update_quantity(product.id, 5)
        assert cart.item_count == 5

    def test_update_quantity_missing_product_raises(self):
        cart = Cart("cust-1")
        with pytest.raises(CartError):
            cart.update_quantity("missing", 3)

    # MISSING: test_update_quantity_to_zero_removes_item
    # MISSING: test_update_quantity_exceeding_stock_raises


class TestCartTotals:
    def test_total(self):
        cart = Cart("cust-1")
        cart.add_item(make_product(price=10.00), quantity=2)
        cart.add_item(make_product(product_id="p2", price=5.00), quantity=1)
        assert cart.total == 25.00

    def test_empty_cart_total(self):
        cart = Cart("cust-1")
        assert cart.total == 0.0

    def test_clear(self):
        cart = Cart("cust-1")
        cart.add_item(make_product())
        cart.clear()
        assert cart.is_empty()
        assert cart.total == 0.0


# MISSING: TestCartCoupon — apply_coupon() completely untested
# MISSING: test_to_dict
