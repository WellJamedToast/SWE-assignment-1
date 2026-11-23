"""SQLite persistence. Contains deliberate reliability/security problems."""
import sqlite3
from models import Product


class OutOfStockError(Exception):
    """Raised when a checkout asks for more stock than is available."""


class StoreRepository:
    def __init__(self, db_path='shop.db'):
        self.db_path = db_path

    def connect(self):
        return sqlite3.connect(self.db_path, timeout=2)

    def get_product(self, sku):
        conn = self.connect()
        # FIX 4: parameterized query instead of an f-string (SQL injection).
        row = conn.execute('SELECT sku, name, price, stock FROM products WHERE sku = ?', (sku,)).fetchone()
        conn.close()
        return Product(*row) if row else None

    def get_saved_cart(self, user_id):
        conn = self.connect()
        # FIX 4: parameterized query instead of an f-string (SQL injection).
        rows = conn.execute('SELECT sku, quantity FROM saved_cart WHERE user_id = ?', (user_id,)).fetchall()
        conn.close()
        return rows

    def save_cart(self, user_id, lines):
        conn = self.connect()
        conn.execute('DELETE FROM saved_cart WHERE user_id = ?', (user_id,))
        for line in lines:
            conn.execute('INSERT INTO saved_cart VALUES (?, ?, ?)', (user_id, line.sku, line.quantity))
        conn.commit()
        conn.close()

    # FIX 5/6/8: update_stock() and save_order() were replaced by the methods below.
    # Stock is reserved and the order row created in ONE transaction, and the
    # decrement only succeeds if enough stock is left.

    def reserve_stock_and_create_order(self, user_id, lines, amount, request_id):
        conn = self.connect()
        try:
            with conn:  # commits on success, rolls back everything on an exception
                # request_id is UNIQUE, so a duplicate raises sqlite3.IntegrityError here.
                cur = conn.execute('INSERT INTO orders(user_id, amount, status, request_id) VALUES (?, ?, ?, ?)',
                                   (user_id, amount, 'pending', request_id))
                for line in lines:
                    updated = conn.execute(
                        'UPDATE products SET stock = stock - ? WHERE sku = ? AND stock >= ?',
                        (line.quantity, line.sku, line.quantity)).rowcount
                    if updated != 1:
                        raise OutOfStockError(line.sku)
                return cur.lastrowid
        finally:
            conn.close()

    def mark_order(self, order_id, status):
        conn = self.connect()
        try:
            with conn:
                conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
        finally:
            conn.close()

    def release_stock_and_mark_order(self, order_id, status, lines):
        """Give reserved stock back after a failed payment and record the status."""
        conn = self.connect()
        try:
            with conn:
                for line in lines:
                    conn.execute('UPDATE products SET stock = stock + ? WHERE sku = ?', (line.quantity, line.sku))
                conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
        finally:
            conn.close()

    def get_order_by_request_id(self, request_id):
        conn = self.connect()
        try:
            return conn.execute('SELECT id, user_id, amount, status FROM orders WHERE request_id = ?',
                                (request_id,)).fetchone()
        finally:
            conn.close()

    def list_orders(self, user_id):
        conn = self.connect()
        rows = conn.execute('SELECT id, user_id, amount, status FROM orders ORDER BY id DESC').fetchall()
        conn.close()
        return rows
