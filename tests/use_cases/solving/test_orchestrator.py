"""Unit tests for the optimization Orchestrator's provider-selection routing."""

import logging

import pytest

from domain.product import Product
from domain.request import Request
from use_cases.solving.optimization.enumeration.enumeration_solution_provider import EnumerationSolutionProvider
from use_cases.solving.optimization.heuristic.heuristic_solution_provider import HeuristicSolutionProvider
from use_cases.solving.optimization.mip_highs.mip_highs_solution_provider import MipHighsSolutionProvider
from use_cases.solving.orchestrator import Orchestrator
from use_cases.solving.postprocessing.postprocessing import PostProcess
from use_cases.solving.preprocessing.preprocessing import PreProcess


@pytest.fixture
def banana() -> Product:
    return Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)


def _orchestrator(
    max_products_for_mip: int = 50,
    max_combinations_for_enumeration: int = 1000,
) -> Orchestrator:
    return Orchestrator(
        preprocessing=PreProcess(),
        postprocessing=PostProcess(),
        mip_solution_provider=MipHighsSolutionProvider(),
        heuristic_solution_provider=HeuristicSolutionProvider(),
        enumeration_solution_provider=EnumerationSolutionProvider(),
        max_products_for_mip=max_products_for_mip,
        max_combinations_for_enumeration=max_combinations_for_enumeration,
    )


def test__orchestrator__given_solvable_request__returns_recommendation(banana, caplog):
    # ARRANGE — small combination space (default thresholds) routes to enumeration
    request = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana])
    orchestrator = _orchestrator()

    # ACT
    with caplog.at_level(logging.INFO):
        result = orchestrator.solve(request)

    # ASSERT — Recommendation should contain selected products and totals
    assert result is not None
    assert result.total_calories > 0
    assert result.total_weight_kg > 0
    assert result.total_cost_usd > 0
    assert "Selected provider: Brute-force Enumeration" in caplog.text


def test__orchestrator__given_no_product_fits__returns_none():
    # ARRANGE — budget too tight to afford any product
    expensive = Product(name="expensive", price_usd=100.0, weight_kg=1.0, calories=100)
    request = Request(max_weight_kg=10.0, max_budget_usd=0.01, products=[expensive])
    orchestrator = _orchestrator()

    # ACT
    result = orchestrator.solve(request)

    # ASSERT — No product fits, so no recommendation exists
    assert result is None


def test__orchestrator__given_enumeration_disabled__routes_small_request_to_mip(banana, caplog):
    # ARRANGE — max_combinations_for_enumeration=0 forces past enumeration, and
    # a 1-product request stays under the default max_products_for_mip, so this
    # must land on MipHighsSolutionProvider.
    request = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana])
    orchestrator = _orchestrator(max_combinations_for_enumeration=0)

    # ACT
    with caplog.at_level(logging.INFO):
        result = orchestrator.solve(request)

    # ASSERT
    assert result is not None
    assert result.total_calories > 0
    assert "Selected provider: MIP (HiGHS)" in caplog.text


def test__orchestrator__given_enumeration_and_mip_disabled__routes_to_heuristic(banana, caplog):
    # ARRANGE — both thresholds forced to 0 leaves only the heuristic path
    request = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana])
    orchestrator = _orchestrator(max_products_for_mip=0, max_combinations_for_enumeration=0)

    # ACT
    with caplog.at_level(logging.INFO):
        result = orchestrator.solve(request)

    # ASSERT — the heuristic isn't guaranteed optimal, only feasible
    assert result is not None
    assert result.total_calories > 0
    assert result.total_cost_usd <= 10.0
    assert result.total_weight_kg <= 5.0
    assert "Selected provider: Greedy Heuristic" in caplog.text
