import pytest
from domain.product import Product
from domain.request import Request
from use_cases.solving.preprocessing.preprocessing import PreProcess


@pytest.fixture
def banana() -> Product:
    return Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)


def test__preprocess__run__passes_request_through_unchanged(banana):
    # ARRANGE
    request = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana])

    # ACT
    result = PreProcess().run(request)

    # ASSERT
    assert result.request is request


def test__preprocess__run__keeps_product_that_fits_within_both_constraints(banana):
    # ARRANGE — banana (0.5 USD, 0.12 kg) is well within the limits
    request = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana])

    # ACT
    result = PreProcess().run(request)

    # ASSERT
    assert result.feasible_products == [banana]


def test__preprocess__run__excludes_product_whose_price_exceeds_budget():
    # ARRANGE — product costs 100 USD but budget is only 5 USD
    expensive = Product(name="truffle", price_usd=100.0, weight_kg=0.1, calories=50)
    request = Request(max_weight_kg=5.0, max_budget_usd=5.0, products=[expensive])

    # ACT
    result = PreProcess().run(request)

    # ASSERT — a single unit already exceeds the budget, so it is filtered out
    assert result.feasible_products == []


def test__preprocess__run__excludes_product_whose_weight_exceeds_capacity():
    # ARRANGE — product weighs 10 kg but capacity is only 1 kg
    heavy = Product(name="watermelon", price_usd=1.0, weight_kg=10.0, calories=300)
    request = Request(max_weight_kg=1.0, max_budget_usd=50.0, products=[heavy])

    # ACT
    result = PreProcess().run(request)

    # ASSERT — a single unit already exceeds the weight limit, so it is filtered out
    assert result.feasible_products == []


def test__preprocess__run__keeps_only_feasible_products_from_mixed_catalogue(banana):
    # ARRANGE — banana fits; boulder does not (too heavy)
    boulder = Product(name="boulder", price_usd=1.0, weight_kg=999.0, calories=1)
    request = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana, boulder])

    # ACT
    result = PreProcess().run(request)

    # ASSERT — only banana survives the filter
    assert result.feasible_products == [banana]
