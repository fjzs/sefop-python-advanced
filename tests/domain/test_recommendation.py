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


def test__recommendation__given_weight_exactly_at_limit_with_float_noise__does_not_raise():
    # ARRANGE — 0.1kg x8 + 2.2kg x11 sums to 25.000000000000004 in float
    # arithmetic: a few ULPs above the mathematically exact 25.0 limit.
    # Reproduces a reported production bug where a solver-feasible solution
    # was rejected by this exact boundary case.
    light = Product(name="light", price_usd=1.0, weight_kg=0.1, calories=10)
    heavy = Product(name="heavy", price_usd=1.0, weight_kg=2.2, calories=10)
    tight_request = Request(max_weight_kg=25.0, max_budget_usd=1000.0, products=[light, heavy])

    # ACT
    rec = Recommendation(request=tight_request, quantities={light: 8, heavy: 11})

    # ASSERT — construction succeeded and holds the requested quantities
    assert rec.quantities == {light: 8, heavy: 11}


def test__recommendation__given_cost_exactly_at_limit_with_float_noise__does_not_raise():
    # ARRANGE — 0.1usd x4 + 0.8usd x12 sums to 10.000000000000002 in float
    # arithmetic: a few ULPs above the mathematically exact 10.0 budget.
    # Same class of bug as the weight case above, on the budget check.
    cheap = Product(name="cheap", price_usd=0.1, weight_kg=1.0, calories=10)
    pricey = Product(name="pricey", price_usd=0.8, weight_kg=1.0, calories=10)
    tight_request = Request(max_weight_kg=1000.0, max_budget_usd=10.0, products=[cheap, pricey])

    # ACT
    rec = Recommendation(request=tight_request, quantities={cheap: 4, pricey: 12})

    # ASSERT — construction succeeded and holds the requested quantities
    assert rec.quantities == {cheap: 4, pricey: 12}
