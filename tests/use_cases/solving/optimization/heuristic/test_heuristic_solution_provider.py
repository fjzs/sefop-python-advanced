import pytest

from domain.product import Product
from domain.request import Request
from use_cases.solving.optimization.heuristic.heuristic_solution_provider import HeuristicSolutionProvider
from use_cases.solving.preprocessing.pre_processed_data import PreProcessedData


@pytest.fixture
def banana() -> Product:
    return Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)


@pytest.fixture
def chips() -> Product:
    return Product(name="chips", price_usd=1.0, weight_kg=0.2, calories=150)


def test__name__returns_human_friendly_label():
    # ACT / ASSERT
    assert HeuristicSolutionProvider().name == "Greedy Heuristic"


def test__solve__when_no_product_fits__returns_none():
    # ARRANGE — budget too tight for any product
    heavy = Product(name="heavy", price_usd=100.0, weight_kg=10.0, calories=500)
    request = Request(max_weight_kg=1.0, max_budget_usd=0.01, products=[heavy])
    provider = HeuristicSolutionProvider()

    # ACT
    data = PreProcessedData(request=request, feasible_products=list(request.products))
    result = provider.solve(data)

    # ASSERT
    assert result is None


def test__solve__picks_maximum_feasible_quantity(banana):
    # ARRANGE — room for exactly 3 bananas by weight (0.36 kg), 4 by budget ($2.00)
    request = Request(max_weight_kg=0.36, max_budget_usd=2.0, products=[banana])
    provider = HeuristicSolutionProvider()

    # ACT
    data = PreProcessedData(request=request, feasible_products=list(request.products))
    result = provider.solve(data)

    # ASSERT
    assert result is not None
    assert result.quantities[banana] == 3


def test__solve__falls_through_to_next_product_when_primary_is_exhausted(banana, chips):
    # ARRANGE
    # chips:  150 / 0.20 = 750 cal/kg  → higher density, picked first
    # banana: 89  / 0.12 = 741 cal/kg  → picked second with remaining capacity
    # weight: 0.52 kg → 2 chips (0.40 kg) + 1 banana (0.12 kg) = 0.52 kg ✓
    # budget: $5.00 — not the binding constraint
    request = Request(max_weight_kg=0.52, max_budget_usd=5.0, products=[banana, chips])
    provider = HeuristicSolutionProvider()

    # ACT
    data = PreProcessedData(request=request, feasible_products=list(request.products))
    result = provider.solve(data)

    # ASSERT
    assert result is not None
    assert chips in result.quantities
    assert banana in result.quantities


def test__solve__picks_highest_calorie_density_first(banana, chips):
    # ARRANGE
    # banana: 89 / 0.12 = 741 cal/kg
    # chips:  150 / 0.20 = 750 cal/kg  → higher density, should be picked first
    # tight budget: only enough for one product
    request = Request(max_weight_kg=0.5, max_budget_usd=1.0, products=[banana, chips])
    provider = HeuristicSolutionProvider()

    # ACT
    data = PreProcessedData(request=request, feasible_products=list(request.products))
    result = provider.solve(data)

    # ASSERT
    assert result is not None
    assert chips in result.quantities
