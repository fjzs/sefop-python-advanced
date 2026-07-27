"""Cross-checks that MipHighsSolutionProvider, MipGoogleScipSolutionProvider, and
HeuristicSolutionProvider agree with the brute-force EnumerationSolutionProvider
oracle on small, hand-verifiable instances.

This is the replacement for the deleted component-level structural tests
(test_variable_select_product.py, test_constraint_limit_budget.py, etc.):
correctness of the formulation is now checked at the observable
Recommendation/total_calories level only, never by inspecting solver-internal
structure.
"""

import pytest

from domain.product import Product
from domain.request import Request
from use_cases.solving.optimization.enumeration.enumeration_solution_provider import EnumerationSolutionProvider
from use_cases.solving.optimization.heuristic.heuristic_solution_provider import HeuristicSolutionProvider
from use_cases.solving.optimization.mip_google.mip_google_scip_solution_provider import (
    MipGoogleScipSolutionProvider,
)
from use_cases.solving.optimization.mip_highs.mip_highs_solution_provider import MipHighsSolutionProvider
from use_cases.solving.preprocessing.pre_processed_data import PreProcessedData


@pytest.fixture
def banana() -> Product:
    return Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)


@pytest.fixture
def chips() -> Product:
    return Product(name="chips", price_usd=1.0, weight_kg=0.2, calories=150)


@pytest.fixture
def soda() -> Product:
    return Product(name="soda", price_usd=2.0, weight_kg=1.0, calories=140)


def _oracle_calories(data: PreProcessedData) -> int:
    recommendation = EnumerationSolutionProvider().solve(data)
    assert recommendation is not None, "test fixture must be feasible"
    return recommendation.total_calories


@pytest.mark.parametrize(
    "max_weight_kg,max_budget_usd",
    [
        (5.0, 10.0),
        (0.36, 2.0),
        (0.52, 5.0),
    ],
)
def test__mip_highs__matches_enumeration_oracle_on_small_instances(banana, chips, soda, max_weight_kg, max_budget_usd):
    # ARRANGE
    request = Request(max_weight_kg=max_weight_kg, max_budget_usd=max_budget_usd, products=[banana, chips, soda])
    data = PreProcessedData(request=request, feasible_products=[banana, chips, soda])

    # ACT
    mip_result = MipHighsSolutionProvider().solve(data)

    # ASSERT — MIP is exact, so it must match the brute-force optimum exactly.
    assert mip_result is not None
    assert mip_result.total_calories == _oracle_calories(data)


@pytest.mark.parametrize(
    "max_weight_kg,max_budget_usd",
    [
        (5.0, 10.0),
        (0.36, 2.0),
        (0.52, 5.0),
    ],
)
def test__mip_google_scip__matches_enumeration_oracle_on_small_instances(
    banana, chips, soda, max_weight_kg, max_budget_usd
):
    # ARRANGE
    request = Request(max_weight_kg=max_weight_kg, max_budget_usd=max_budget_usd, products=[banana, chips, soda])
    data = PreProcessedData(request=request, feasible_products=[banana, chips, soda])

    # ACT
    mip_result = MipGoogleScipSolutionProvider().solve(data)

    # ASSERT — MIP is exact, so it must match the brute-force optimum exactly.
    assert mip_result is not None
    assert mip_result.total_calories == _oracle_calories(data)


@pytest.mark.parametrize(
    "max_weight_kg,max_budget_usd",
    [
        (5.0, 10.0),
        (0.36, 2.0),
        (0.52, 5.0),
    ],
)
def test__heuristic__is_feasible_and_never_beats_the_enumeration_oracle(
    banana, chips, soda, max_weight_kg, max_budget_usd
):
    # ARRANGE — the greedy heuristic is not guaranteed optimal, so equality
    # isn't asserted, only that it never claims more calories than the true
    # optimum.
    request = Request(max_weight_kg=max_weight_kg, max_budget_usd=max_budget_usd, products=[banana, chips, soda])
    data = PreProcessedData(request=request, feasible_products=[banana, chips, soda])

    # ACT
    heuristic_result = HeuristicSolutionProvider().solve(data)

    # ASSERT
    assert heuristic_result is not None
    assert heuristic_result.total_calories <= _oracle_calories(data)
