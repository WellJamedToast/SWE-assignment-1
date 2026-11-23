"""Unit tests for CheckoutService fixes (defects 5-8), using fake payment gateways."""
import pytest

from checkout import CheckoutService
from conftest import RaisingGateway, set_stock
from payments import FakePaymentGateway


def test_successful_checkout_charges_reserves_stock_and_clears_cart(service, gateway, cart, repo):
    cart.add_item('MOU-01', 2)
    result = service.checkout(cart, 'tok', 'r1')

    assert result.status == 'paid'
    assert len(gateway.calls) == 1
    assert repo.get_product('MOU-01').stock == 18
    assert cart.lines == []


# Defects 5 and 7: declined payment kept the stock decrement and emptied the cart
def test_declined_payment_restores_stock_and_keeps_cart(repo, cart):
    service = CheckoutService(repo, FakePaymentGateway(should_approve=False))
    cart.add_item('LAP-01', 2)
    result = service.checkout(cart, 'tok', 'r1')

    assert result.status == 'declined'
    assert repo.get_product('LAP-01').stock == 5
    assert cart.lines[0].quantity == 2


def test_gateway_exception_restores_stock_and_keeps_cart(repo, cart):
    service = CheckoutService(repo, RaisingGateway())
    cart.add_item('USB-01', 3)
    result = service.checkout(cart, 'tok', 'r1')

    assert result.status == 'payment_error'
    assert repo.get_product('USB-01').stock == 50
    assert len(cart.lines) == 1


# Defect 6: stock changed after adding to cart -> oversell / negative stock
def test_stock_changed_after_adding_to_cart_is_not_charged(service, gateway, cart, repo, db_path):
    cart.add_item('LAP-01', 2)
    set_stock(db_path, 'LAP-01', 1)        # someone else bought them meanwhile
    result = service.checkout(cart, 'tok', 'r1')

    assert result.status == 'out_of_stock'
    assert gateway.calls == []
    assert repo.get_product('LAP-01').stock == 1


def test_stock_reservation_is_all_or_nothing(service, cart, repo, db_path):
    cart.add_item('USB-01', 5)
    cart.add_item('LAP-01', 2)
    set_stock(db_path, 'LAP-01', 0)
    result = service.checkout(cart, 'tok', 'r1')

    assert result.status == 'out_of_stock'
    assert repo.get_product('USB-01').stock == 50   # first line rolled back too


# Defect 8: repeated checkout charged twice
def test_repeated_checkout_with_same_request_id_charges_once(service, gateway, cart, repo):
    cart.add_item('USB-01', 2)
    first = service.checkout(cart, 'tok', 'r1')
    cart.add_item('USB-01', 1)             # user clicks "Pay" again
    second = service.checkout(cart, 'tok', 'r1')

    assert second.order_id == first.order_id
    assert len(gateway.calls) == 1
    assert repo.get_product('USB-01').stock == 48
