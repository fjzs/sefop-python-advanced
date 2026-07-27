import math

import pytest

from domain.product import Product
from domain.request import Request


@pytest.fixture
def banana() -> Product:
    return Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)


@pytest.fixture
def chips() -> Product:
    return Product(name="chips", price_usd=1.0, weight_kg=0.2, calories=150)


def test__request__given_valid_inputs__creates_successfully(banana, chips):
    # ARRANGE / ACT
    request = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana, chips])

    # ASSERT
    assert math.isclose(request.max_weight_kg, 5.0)
    assert math.isclose(request.max_budget_usd, 10.0)
    assert request.products == [banana, chips]


@pytest.mark.parametrize("weight", [0, -1, -0.001])
def test__request__given_non_positive_max_weight__raises_value_error(weight, banana):
    # ACT / ASSERT
    with pytest.raises(ValueError, match="max_weight_kg"):
        Request(max_weight_kg=weight, max_budget_usd=10.0, products=[banana])


@pytest.mark.parametrize("budget", [0, -1, -0.01])
def test__request__given_non_positive_max_budget__raises_value_error(budget, banana):
    # ACT / ASSERT
    with pytest.raises(ValueError, match="max_budget_usd"):
        Request(max_weight_kg=5.0, max_budget_usd=budget, products=[banana])


def test__request__given_empty_products__raises_value_error():
    # ACT / ASSERT
    with pytest.raises(ValueError, match="products"):
        Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[])


def test__request__given_duplicate_product_names__raises_value_error():
    # ARRANGE
    apple1 = Product(name="apple", price_usd=0.3, weight_kg=0.1, calories=52)
    apple2 = Product(name="apple", price_usd=0.5, weight_kg=0.15, calories=60)

    # ACT / ASSERT
    with pytest.raises(ValueError, match="duplicate"):
        Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[apple1, apple2])
