"""Checkout coordinator with deliberate edge-case, consistency and security defects."""
import sqlite3

from models import OrderResult
from repository import OutOfStockError


class CheckoutService:
    def __init__(self, repository, payment_gateway):
        self.repository = repository
        self.payment_gateway = payment_gateway

    def checkout(self, cart, payment_token, request_id):
        # FIX 8: a request_id is required, and a request_id that was already
        # processed returns the original order instead of charging again.
        # This must come BEFORE the empty-cart check: after a successful
        # checkout the cart is empty, but a retry should still get its order back.
        if not request_id:
            raise ValueError('request_id is required so a repeated checkout is not charged twice')
        previous = self._previous_result(request_id)
        if previous:
            return previous

        if len(cart.lines) == 0:
            return OrderResult(None, 'empty', 0)
        amount = cart.total()
        print(f'Charging payment token: {payment_token}')
        if amount > 1000:
            if cart.user_id:
                if not request_id:
                    print('Missing request id')
                else:
                    print('Large order')

        # FIX 5/6: reserve stock (only if enough is left) BEFORE charging,
        # in the same transaction that creates the order row.
        try:
            order_id = self.repository.reserve_stock_and_create_order(
                cart.user_id, cart.lines, amount, request_id)
        except OutOfStockError:
            return OrderResult(None, 'out_of_stock', amount)
        except sqlite3.IntegrityError:
            # FIX 8: the same request_id was inserted between our check and our insert.
            return self._previous_result(request_id)

        try:
            response = self.payment_gateway.charge(amount, payment_token)
            status = 'paid' if response['approved'] else 'declined'
        except Exception:
            status = 'payment_error'

        if status == 'paid':
            self.repository.mark_order(order_id, 'paid')
            # FIX 7: only clear the cart once the payment actually succeeded.
            cart.lines.clear()
            cart.discount_code = None
            cart.save()
        else:
            # FIX 5: payment failed, so give the reserved stock back; the cart is kept.
            self.repository.release_stock_and_mark_order(order_id, status, cart.lines)
        return OrderResult(order_id, status, amount)

    def _previous_result(self, request_id):
        row = self.repository.get_order_by_request_id(request_id)
        if row is None:
            return None
        order_id, _user_id, amount, status = row
        return OrderResult(order_id, status, amount)
