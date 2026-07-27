import math
import pytest
from domain.product import Product
from domain.request import Request
from domain.recommendation import Recommendation
from use_cases.solving.postprocessing.postprocessing import PostProcess


@pytest.fixture
def banana() -> Product:
    return Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)


@pytest.fixture
def chips() -> Product:
    return Product(name="chips", price_usd=1.0, weight_kg=0.2, calories=150)


def test__postprocess__run__sorts_quantities_highest_first(banana, chips):
    # ARRANGE — banana 2x, chips 5x, passed in ascending order
    request = Request(max_weight_kg=5.0, max_budget_usd=20.0, products=[banana, chips])
    rec = Recommendation(request=request, quantities={banana: 2, chips: 5})

    # ACT
    result = PostProcess().run(rec)

    # ASSERT — chips (5) should come before banana (2)
    assert list(result.quantities.keys()) == [chips, banana]


def test__postprocess__run__preserves_totals(banana, chips):
    # ARRANGE
    request = Request(max_weight_kg=5.0, max_budget_usd=20.0, products=[banana, chips])
    rec = Recommendation(request=request, quantities={banana: 2, chips: 5})

    # ACT
    result = PostProcess().run(rec)

    # ASSERT — sorting must not change any totals
    assert result.total_calories == rec.total_calories
    assert math.isclose(result.total_cost_usd, rec.total_cost_usd)
    assert math.isclose(result.total_weight_kg, rec.total_weight_kg)


def test__postprocess__run__single_product_unchanged(banana):
    # ARRANGE — only one product; order is trivially correct
    request = Request(max_weight_kg=5.0, max_budget_usd=20.0, products=[banana])
    rec = Recommendation(request=request, quantities={banana: 3})

    # ACT
    result = PostProcess().run(rec)

    # ASSERT
    assert list(result.quantities.keys()) == [banana]
    assert result.quantities[banana] == 3
