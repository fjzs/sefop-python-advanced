import math

import pytest

from domain.product import Product
from domain.recommendation import Recommendation
from domain.request import Request


@pytest.fixture
def banana() -> Product:
    return Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)


@pytest.fixture
def chips() -> Product:
    return Product(name="chips", price_usd=1.0, weight_kg=0.2, calories=150)


@pytest.fixture
def picnic_request(banana, chips) -> Request:
    return Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana, chips])


def test__recommendation__given_valid_inputs__computes_totals_correctly(picnic_request, banana, chips):
    # ARRANGE / ACT
    # 2 bananas + 1 chips
    rec = Recommendation(request=picnic_request, quantities={banana: 2, chips: 1})

    # ASSERT
    assert rec.total_calories == 2 * 89 + 1 * 150  # 328
    assert math.isclose(rec.total_cost_usd, 2 * 0.5 + 1 * 1.0)  # 2.0
    assert math.isclose(rec.total_weight_kg, 2 * 0.12 + 1 * 0.2)  # 0.44


def test__recommendation__given_empty_quantities__raises_value_error(picnic_request):
    # ACT / ASSERT
    with pytest.raises(ValueError, match="quantities"):
        Recommendation(request=picnic_request, quantities={})


def test__recommendation__given_quantity_less_than_one__raises_value_error(picnic_request, banana):
    # ACT / ASSERT
    with pytest.raises(ValueError, match="quantity"):
        Recommendation(request=picnic_request, quantities={banana: 0})


def test__recommendation__given_product_not_in_request__raises_value_error(picnic_request):
    # ARRANGE — a product that was never included in the request
    stranger = Product(name="stranger", price_usd=1.0, weight_kg=0.1, calories=100)

    # ACT / ASSERT
    with pytest.raises(ValueError, match="not in request"):
        Recommendation(request=picnic_request, quantities={stranger: 1})


def test__recommendation__given_total_cost_exceeds_budget__raises_value_error(banana, chips):
    # ARRANGE — tight budget: only 1.0 usd, but we pick 3 chips at 1.0 each
    tight_request = Request(max_weight_kg=5.0, max_budget_usd=1.0, products=[banana, chips])

    # ACT / ASSERT
    with pytest.raises(ValueError, match="budget"):
        Recommendation(request=tight_request, quantities={chips: 3})


def test__recommendation__given_total_weight_exceeds_limit__raises_value_error(banana, chips):
    # ARRANGE — tight weight: only 0.1 kg, but chips weigh 0.2 kg
    tight_request = Request(max_weight_kg=0.1, max_budget_usd=10.0, products=[banana, chips])

    # ACT / ASSERT
    with pytest.raises(ValueError, match="weight"):
        Recommendation(request=tight_request, quantities={chips: 1})
