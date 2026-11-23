"""Shared fixtures: every test gets its own temporary SQLite database."""
import sqlite3

import pytest

from cart import ShoppingCart
from checkout import CheckoutService
from payments import FakePaymentGateway
from repository import StoreRepository
from setup_db import initialize


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / 'test.db')
    initialize(path)
    return path


@pytest.fixture
def repo(db_path):
    return StoreRepository(db_path)


@pytest.fixture
def cart(repo):
    return ShoppingCart('alice', repo)


@pytest.fixture
def gateway():
    return FakePaymentGateway(should_approve=True)


@pytest.fixture
def service(repo, gateway):
    return CheckoutService(repo, gateway)


def set_stock(db_path, sku, stock):
    """Simulate another customer changing stock behind our back."""
    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute('UPDATE products SET stock = ? WHERE sku = ?', (stock, sku))
    conn.close()


class RaisingGateway:
    """Fake gateway that fails unexpectedly, e.g. a network timeout."""

    def __init__(self):
        self.calls = []

    def charge(self, amount, payment_token):
        self.calls.append((amount, payment_token))
        raise TimeoutError('gateway timed out')
