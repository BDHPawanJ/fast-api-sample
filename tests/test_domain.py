"""Unit tests for domain entities: plain Python, no database or mocks."""

from decimal import Decimal

import pytest

from app.domain.cart import Cart
from app.domain.errors import (
    CartItemNotFound,
    InsufficientStock,
    InvalidProduct,
    InvalidQuantity,
)
from app.domain.product import Product
from app.domain.user import User


def _product(id: int = 1, stock: int = 10) -> Product:
    return Product(id=id, name=f"Product {id}", price=Decimal("10.0"), stock=stock)


class TestProduct:
    """Product invariants and stock helpers."""

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"name": "", "price": Decimal("1.0")},
            {"name": "x", "price": Decimal("0")},
            {"name": "x", "price": Decimal("-1.0")},
            {"name": "x", "price": Decimal("1.0"), "stock": -1},
        ],
    )
    def test_rejects_invalid_state(self, kwargs):
        with pytest.raises(InvalidProduct):
            Product(**kwargs)

    def test_new_product_gets_public_id(self):
        assert (
            Product(name="a", price=Decimal("1.0")).public_id
            != Product(name="a", price=Decimal("1.0")).public_id
        )

    def test_update_details_applies_changes(self):
        product = _product()
        product.update_details(name="Renamed", price=Decimal("20.0"))
        assert (product.name, product.price) == ("Renamed", 20.0)

    def test_update_details_is_atomic_on_invalid_change(self):
        product = _product()
        with pytest.raises(InvalidProduct):
            product.update_details(name="Renamed", price=Decimal("-5.0"))
        assert (product.name, product.price) == ("Product 1", 10.0)

    def test_update_details_rejects_unknown_field(self):
        with pytest.raises(InvalidProduct):
            _product().update_details(public_id="hijack")

    @pytest.mark.parametrize(
        "stock,in_stock,low", [(0, False, False), (1, True, True), (11, True, False)]
    )
    def test_stock_helpers(self, stock, in_stock, low):
        product = _product(stock=stock)
        assert product.is_in_stock is in_stock
        assert product.is_low_stock() is low


class TestProductPrice:
    """Prices are exact, whole-cent Decimals that fit the DB column."""

    def test_float_price_is_a_programming_error(self):
        with pytest.raises(TypeError):
            Product(name="x", price=1.0)  # type: ignore[arg-type]

    def test_price_is_normalized_to_cents(self):
        assert Product(name="x", price=Decimal("10.5")).price.as_tuple() == (
            Decimal("10.50").as_tuple()
        )
        assert Product(name="x", price=Decimal("10.500")).price == Decimal("10.50")

    @pytest.mark.parametrize(
        "price", [Decimal("0.001"), Decimal("NaN"), Decimal("Infinity")]
    )
    def test_rejects_sub_cent_and_non_finite(self, price):
        with pytest.raises(InvalidProduct):
            Product(name="x", price=price)

    def test_rejects_price_above_column_capacity(self):
        Product(name="x", price=Product.MAX_PRICE)
        with pytest.raises(InvalidProduct):
            Product(name="x", price=Product.MAX_PRICE + Product.CENT)

    def test_type_error_in_update_leaves_product_unchanged(self):
        product = _product()
        with pytest.raises(TypeError):
            product.update_details(name="Renamed", price=5.0)
        assert (product.name, product.price) == ("Product 1", Decimal("10.00"))


class TestUser:
    """User account status."""

    def test_email_is_case_insensitive(self):
        assert User(email=" Alice@Example.COM ", hashed_password="h").email == (
            "alice@example.com"
        )

    def test_activate_and_deactivate(self):
        user = User(email="a@example.com", hashed_password="hash")
        user.deactivate()
        assert user.is_active is False
        user.activate()
        assert user.is_active is True


class TestCart:
    """Cart aggregate rules."""

    def test_add_item_creates_and_merges_lines(self):
        cart = Cart(user_id=1)
        product = _product(stock=10)

        cart.add_item(product, 2)
        cart.add_item(product, 3)

        assert len(cart.items) == 1
        assert cart.quantity_of(product.id) == 5
        assert cart.total_quantity == 5

    def test_add_item_rejects_non_positive_quantity(self):
        with pytest.raises(InvalidQuantity):
            Cart(user_id=1).add_item(_product(), 0)

    def test_add_item_checks_merged_quantity_against_stock(self):
        cart = Cart(user_id=1)
        product = _product(stock=4)
        cart.add_item(product, 3)

        with pytest.raises(InsufficientStock):
            cart.add_item(product, 2)
        assert cart.quantity_of(product.id) == 3

    def test_quantity_limit_per_line(self):
        product = _product(stock=1000)
        with pytest.raises(InvalidQuantity):
            Cart(user_id=1).add_item(product, Cart.MAX_QUANTITY_PER_LINE + 1)

    def test_add_unpersisted_product_is_a_programming_error(self):
        with pytest.raises(ValueError):
            Cart(user_id=1).add_item(Product(name="new", price=Decimal("1.0"), stock=5))

    def test_set_quantity_replaces_and_zero_removes(self):
        cart = Cart(user_id=1)
        product = _product()
        cart.add_item(product, 2)

        cart.set_quantity(product, 7)
        assert cart.quantity_of(product.id) == 7

        cart.set_quantity(product, 0)
        assert cart.is_empty

    def test_set_quantity_rejects_negative(self):
        with pytest.raises(InvalidQuantity):
            Cart(user_id=1).set_quantity(_product(), -1)

    def test_remove_missing_item_raises(self):
        with pytest.raises(CartItemNotFound):
            Cart(user_id=1).remove_item(42)

    def test_clear(self):
        cart = Cart(user_id=1)
        cart.add_item(_product(id=1))
        cart.add_item(_product(id=2))
        cart.clear()
        assert cart.is_empty
