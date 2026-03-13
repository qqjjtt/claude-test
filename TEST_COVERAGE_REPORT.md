# Test Coverage Report

> Generated: 2026-03-13
> Tool: `pytest-cov` + `coverage.py`
> Test suite: 47 tests, all passing

---

## Overall Coverage Summary

| Module | Stmts | Missed | **Coverage** |
|---|---|---|---|
| `src/notifications.py` | 46 | 46 | **0%** |
| `src/cart.py` | 59 | 13 | **78%** |
| `src/pricing.py` | 59 | 13 | **78%** |
| `src/inventory.py` | 46 | 7 | **85%** |
| `src/models.py` | 86 | 9 | **90%** |
| **TOTAL** | **296** | **88** | **70%** |

A 70% overall line coverage is a reasonable starting point, but the gaps identified below
represent real risk: untested branches are where bugs hide in production.

---

## Priority 1 — Critical (fix immediately)

### `src/notifications.py` — **0% coverage**

Every line of the notification service is completely untested. This is the highest-risk
module because notification bugs are often invisible during development and only surface
when customers are affected (e.g., a shipped order silently fails to notify the customer).

**What to add:**

```python
# tests/test_notifications.py

class TestNotificationService:
    def _make_service(self):
        channel = EmailChannel(smtp_host="localhost")
        return NotificationService(channel), channel

    def test_notify_order_placed_sends_email(self):
        service, channel = self._make_service()
        order = make_order()
        service.notify_order_placed("customer@example.com", order)
        assert len(channel.sent_messages) == 1
        msg = channel.sent_messages[0]
        assert "Confirmation" in msg["subject"]
        assert order.id in msg["body"]

    def test_notify_order_shipped(self): ...
    def test_notify_order_cancelled_includes_refund_amount(self): ...
    def test_notify_low_stock(self): ...
    def test_notify_out_of_stock(self): ...
    def test_channel_send_failure_propagates(self): ...  # mock send() returning False
```

**Key risk:** The `notify_order_cancelled` method formats a refund total — a trivial
arithmetic mistake there would mean customers see a wrong refund amount with no test
catching it.

---

## Priority 2 — High (address this sprint)

### `src/cart.py` — **78% coverage** (lines 21, 33, 57–58, 61, 71, 78, 93–101, 104 uncovered)

#### 2a. `apply_coupon()` — completely untested (lines 93–101)

The entire coupon subsystem has zero test coverage. This is business-critical logic.

```python
class TestCartCoupon:
    def test_valid_coupon_returns_discount(self):
        cart = Cart("cust-1")
        cart.add_item(make_product(price=100.0), quantity=1)
        discount = cart.apply_coupon("SAVE10")
        assert discount == pytest.approx(10.0)

    def test_coupon_is_case_insensitive(self):
        cart = Cart("cust-1")
        cart.add_item(make_product(price=100.0))
        assert cart.apply_coupon("save10") == pytest.approx(10.0)

    def test_invalid_coupon_raises(self):
        cart = Cart("cust-1")
        with pytest.raises(CartError, match="Invalid coupon"):
            cart.apply_coupon("BOGUS")

    def test_halfoff_coupon(self): ...
    def test_save20_coupon(self): ...
    def test_coupon_on_empty_cart_returns_zero(self): ...
```

#### 2b. `update_quantity()` edge cases (lines 57–58, 61)

Setting quantity to `0` should silently remove the item, and exceeding stock should raise.
Neither is tested.

```python
def test_update_quantity_to_zero_removes_item():
    cart = Cart("cust-1")
    cart.add_item(make_product(stock=10))
    cart.update_quantity("p1", 0)
    assert cart.is_empty()

def test_update_quantity_exceeding_stock_raises():
    cart = Cart("cust-1")
    cart.add_item(make_product(stock=5), quantity=2)
    with pytest.raises(CartError, match="Insufficient stock"):
        cart.update_quantity("p1", 10)
```

#### 2c. `add_item()` with non-positive quantity (line 21)

```python
def test_add_item_zero_quantity_raises():
    with pytest.raises(CartError, match="Quantity must be positive"):
        Cart("c").add_item(make_product(), quantity=0)

def test_add_item_negative_quantity_raises():
    with pytest.raises(CartError):
        Cart("c").add_item(make_product(), quantity=-3)
```

### `src/pricing.py` — **78% coverage** (lines 13, 39–47, 56, 59–61, 71 uncovered)

#### 2d. `CategoryDiscountRule` — completely untested (lines 39–47)

```python
class TestCategoryDiscountRule:
    def test_applies_to_matching_category(self):
        rule = CategoryDiscountRule(category="electronics", discount_percent=15)
        items = [
            make_item(price=100.0, quantity=1, category="electronics"),
            make_item(price=50.0, quantity=1, category="clothing", product_id="p2"),
        ]
        assert rule.apply(items) == pytest.approx(15.0)  # only electronics discounted

    def test_category_match_is_case_insensitive(self): ...
    def test_no_matching_items_returns_zero(self): ...
```

#### 2e. `FreeShippingRule` — completely untested (lines 59–61)

```python
class TestFreeShippingRule:
    def test_shipping_cost_below_threshold(self):
        rule = FreeShippingRule(min_order_value=50.0)
        assert rule.shipping_cost(30.0) == 9.99

    def test_free_shipping_at_threshold(self):
        rule = FreeShippingRule(min_order_value=50.0)
        assert rule.shipping_cost(50.0) == 0.0

    def test_free_shipping_above_threshold(self): ...
```

#### 2f. `format_price()` — only USD tested (line 71)

```python
def test_format_price_eur():
    assert format_price(9.99, "EUR") == "€9.99"

def test_format_price_unknown_currency_uses_code_prefix():
    assert format_price(9.99, "JPY") == "JPY 9.99"

def test_format_price_default_is_usd():
    assert format_price(5.0) == "$5.00"
```

---

## Priority 3 — Medium (address next sprint)

### `src/models.py` — **90% coverage** (lines 48, 69, 73, 95, 135–143 uncovered)

#### 3a. `Order.ship()` — not tested at all (lines 135–140)

```python
def test_ship_from_processing_succeeds():
    order = make_order(status=OrderStatus.PROCESSING)
    order.ship()
    assert order.status == OrderStatus.SHIPPED

def test_ship_from_pending_raises():
    order = make_order(status=OrderStatus.PENDING)
    with pytest.raises(ValueError, match="PROCESSING"):
        order.ship()

def test_ship_from_cancelled_raises():
    order = make_order(status=OrderStatus.CANCELLED)
    with pytest.raises(ValueError):
        order.ship()
```

#### 3b. `Product.apply_discount()` boundary values (lines 69, 73)

```python
def test_apply_discount_zero_percent_returns_full_price():
    p = make_product(price=10.0)
    assert p.apply_discount(0) == pytest.approx(10.0)

def test_apply_discount_100_percent_returns_zero():
    p = make_product(price=10.0)
    assert p.apply_discount(100) == pytest.approx(0.0)

def test_apply_discount_negative_raises():
    with pytest.raises(ValueError):
        make_product().apply_discount(-5)

def test_apply_discount_over_100_raises():
    with pytest.raises(ValueError):
        make_product().apply_discount(101)
```

#### 3c. `Address.__str__` with state (line 48)

```python
def test_str_with_state():
    addr = Address(street="1 Main St", city="Springfield", country="US",
                   postal_code="12345", state="IL")
    assert str(addr) == "1 Main St, Springfield, IL, 12345, US"
```

#### 3d. `Order.to_dict()` and `Product.to_dict()` (lines 95, 143)

Serialization methods are commonly called by API layers. Add round-trip or structural
assertions:

```python
def test_order_to_dict_has_required_keys():
    order = make_order()
    d = order.to_dict()
    for key in ("id", "customer_id", "items", "total", "status", "shipping_address"):
        assert key in d

def test_product_to_dict():
    p = Product(id="p1", name="Widget", price=9.99, stock=5, category="gadgets")
    assert p.to_dict()["price"] == 9.99
```

### `src/inventory.py` — **85% coverage** (lines 40, 54, 58, 62, 65, 71, 74 uncovered)

```python
def test_out_of_stock_products():
    mgr = InventoryManager()
    mgr.register_product(make_product(product_id="p1", stock=0))
    mgr.register_product(make_product(product_id="p2", stock=5))
    assert [p.id for p in mgr.out_of_stock_products()] == ["p1"]

def test_total_inventory_value():
    mgr = InventoryManager()
    mgr.register_product(make_product(product_id="p1", price=10.0, stock=3))
    mgr.register_product(make_product(product_id="p2", price=5.0, stock=4))
    assert mgr.total_inventory_value() == pytest.approx(50.0)

def test_search_by_category():
    mgr = InventoryManager()
    mgr.register_product(make_product(product_id="p1", category="gadgets"))
    mgr.register_product(make_product(product_id="p2", category="clothing"))
    results = mgr.search_by_category("gadgets")
    assert len(results) == 1 and results[0].id == "p1"

def test_search_by_tag():
    mgr = InventoryManager()
    mgr.register_product(make_product(product_id="p1", tags=["sale", "new"]))
    mgr.register_product(make_product(product_id="p2", tags=["new"]))
    assert len(mgr.search_by_tag("sale")) == 1

def test_set_low_stock_threshold_negative_raises():
    mgr = InventoryManager()
    with pytest.raises(InventoryError):
        mgr.set_low_stock_threshold(-1)

def test_deduct_stock_unknown_product_raises():
    mgr = InventoryManager()
    with pytest.raises(InventoryError):
        mgr.deduct_stock("ghost", 1)
```

---

## Priority 4 — Structural Improvements

Beyond line coverage, the following structural gaps should be addressed:

### 4a. No integration tests

Currently all tests are pure unit tests. Add at least one end-to-end flow test that
exercises the full purchase cycle:

```
Cart → checkout → Order creation → Inventory deduction → Notification dispatch
```

### 4b. No property-based tests

Boundary conditions like discount percentages, quantities, and prices are ideal candidates
for [Hypothesis](https://hypothesis.readthedocs.io/) property-based testing:

```python
from hypothesis import given, strategies as st

@given(st.floats(min_value=0, max_value=100))
def test_apply_discount_always_returns_non_negative(percent):
    p = Product(id="p", name="X", price=50.0, stock=1, category="x")
    assert p.apply_discount(percent) >= 0
```

### 4c. No tests for concurrent access

`InventoryManager.deduct_stock()` has a TOCTOU (time-of-check-time-of-use) race condition
if called concurrently. Add a test that simulates concurrent deductions to verify the
correct behaviour (or document that external locking is required).

### 4d. No mutation testing

Consider running [mutmut](https://github.com/boxed/mutmut) to verify that existing tests
actually catch code changes. A 90% line coverage score can still pass with tests that make
no assertions (just checking that code doesn't throw).

---

## Recommended Coverage Targets

| Module | Current | Target |
|---|---|---|
| `src/notifications.py` | 0% | ≥ 90% |
| `src/cart.py` | 78% | ≥ 95% |
| `src/pricing.py` | 78% | ≥ 95% |
| `src/inventory.py` | 85% | ≥ 95% |
| `src/models.py` | 90% | ≥ 95% |
| **TOTAL** | **70%** | **≥ 90%** |

Enforce these in CI by adding `--cov-fail-under=90` to the pytest invocation.
