"""Unit tests for StoreRepository fixes (defect 4: SQL injection)."""
from models import CartLine


def test_get_product_is_not_vulnerable_to_sql_injection(repo):
    # With the original f-string query this returned the first product.
    assert repo.get_product("' OR '1'='1") is None
    assert repo.get_product('USB-01').name == 'USB cable'


def test_get_saved_cart_is_not_vulnerable_to_sql_injection(repo):
    repo.save_cart('alice', [CartLine('USB-01', 'USB cable', 9.99, 2)])
    # With the original query this returned alice's saved cart.
    assert repo.get_saved_cart("' OR '1'='1") == []
    assert repo.get_saved_cart('alice') == [('USB-01', 2)]
