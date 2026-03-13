"""
Tests for src/inventory.py

Coverage gaps:
  - InventoryManager.search_by_tag() — not tested
  - InventoryManager.search_by_category() — not tested
  - InventoryManager.total_inventory_value() — not tested
  - InventoryManager.set_low_stock_threshold() with invalid value — not tested
  - InventoryManager.out_of_stock_products() — not tested
  - InventoryManager.all_products() — not tested
"""
import pytest
from src.models import Product
from src.inventory import InventoryManager, InventoryError


def make_product(product_id="p1", name="Widget", price=9.99, stock=10, category="gadgets", tags=None):
    p = Product(id=product_id, name=name, price=price, stock=stock, category=category)
    if tags:
        p.tags = tags
    return p


class TestRegisterProduct:
    def test_register_new_product(self):
        mgr = InventoryManager()
        product = make_product()
        mgr.register_product(product)
        assert mgr.get_product("p1") is product

    def test_register_duplicate_raises(self):
        mgr = InventoryManager()
        product = make_product()
        mgr.register_product(product)
        with pytest.raises(InventoryError, match="already registered"):
            mgr.register_product(product)

    def test_get_unknown_product_returns_none(self):
        mgr = InventoryManager()
        assert mgr.get_product("unknown") is None


class TestRestock:
    def test_restock_increases_stock(self):
        mgr = InventoryManager()
        product = make_product(stock=5)
        mgr.register_product(product)
        mgr.restock("p1", 10)
        assert mgr.get_product("p1").stock == 15

    def test_restock_zero_quantity_raises(self):
        mgr = InventoryManager()
        mgr.register_product(make_product())
        with pytest.raises(InventoryError):
            mgr.restock("p1", 0)

    def test_restock_unknown_product_raises(self):
        mgr = InventoryManager()
        with pytest.raises(InventoryError, match="Unknown product"):
            mgr.restock("nonexistent", 5)


class TestDeductStock:
    def test_deduct_reduces_stock(self):
        mgr = InventoryManager()
        mgr.register_product(make_product(stock=10))
        mgr.deduct_stock("p1", 3)
        assert mgr.get_product("p1").stock == 7

    def test_deduct_insufficient_stock_raises(self):
        mgr = InventoryManager()
        mgr.register_product(make_product(stock=2))
        with pytest.raises(InventoryError, match="Insufficient stock"):
            mgr.deduct_stock("p1", 5)

    def test_deduct_negative_quantity_raises(self):
        mgr = InventoryManager()
        mgr.register_product(make_product())
        with pytest.raises(InventoryError):
            mgr.deduct_stock("p1", -1)

    # MISSING: test_deduct_unknown_product_raises


class TestLowStock:
    def test_low_stock_products(self):
        mgr = InventoryManager()
        mgr.register_product(make_product(product_id="p1", stock=3))
        mgr.register_product(make_product(product_id="p2", stock=20))
        low = mgr.low_stock_products()
        assert len(low) == 1
        assert low[0].id == "p1"

    def test_set_low_stock_threshold(self):
        mgr = InventoryManager()
        mgr.register_product(make_product(product_id="p1", stock=8))
        mgr.set_low_stock_threshold(10)
        assert len(mgr.low_stock_products()) == 1

    # MISSING: test_set_low_stock_threshold_negative_raises
    # MISSING: test_out_of_stock_products
    # MISSING: test_total_inventory_value
    # MISSING: test_search_by_category
    # MISSING: test_search_by_tag
    # MISSING: test_all_products
