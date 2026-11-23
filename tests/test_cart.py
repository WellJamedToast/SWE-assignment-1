"""Unit tests for ShoppingCart fixes (defects 1-3)."""
import pytest


# Defect 1: stale / compounding discount
def test_discount_recalculates_after_cart_is_edited(cart):
    cart.add_item('MOU-01', 1)            # 29.95
    cart.apply_discount('STUDENT20')
    cart.add_item('MOU-01', 1)            # subtotal now 59.90
    assert cart.total() == pytest.approx(59.90 * 0.8)


def test_applying_discount_twice_does_not_compound(cart):
    cart.add_item('USB-01', 10)           # 99.90
    cart.apply_discount('WELCOME10')
    cart.apply_discount('WELCOME10')
    assert cart.total() == pytest.approx(89.91)


# Defect 2: stock check ignored quantity already in the cart
def test_combined_quantity_cannot_exceed_stock(cart):
    assert cart.add_item('LAP-01', 3)     # stock is 5
    assert cart.add_item('LAP-01', 3) is False
    assert cart.lines[0].quantity == 3


# Defect 3: repeated load duplicated quantities
def test_repeated_load_does_not_duplicate_quantities(cart):
    cart.add_item('USB-01', 2)
    cart.save()
    cart.load()
    cart.load()
    assert len(cart.lines) == 1
    assert cart.lines[0].quantity == 2
