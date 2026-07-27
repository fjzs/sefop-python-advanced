from pathlib import Path

import pytest

from domain.product import Product
from domain.request import Request
from use_cases.ports.base_data_loader import BaseDataLoader
from use_cases.solving.optimization.enumeration.enumeration_solution_provider import EnumerationSolutionProvider
from use_cases.solving.optimization.heuristic.heuristic_solution_provider import HeuristicSolutionProvider
from use_cases.solving.optimization.mip_highs.mip_highs_solution_provider import MipHighsSolutionProvider
from use_cases.solving.orchestrator import Orchestrator
from use_cases.solving.postprocessing.postprocessing import PostProcess
from use_cases.solving.preprocessing.preprocessing import PreProcess
from use_cases.use_case_solve_single_request import SolveSingleRequest


class _FakeDataLoader(BaseDataLoader):
    """Test double returning a fixed Request, or None for "not found"."""

    def __init__(self, request: Request | None) -> None:
        self._request = request

    def load(self, request_id: str) -> Request | None:
        return self._request


def _orchestrator() -> Orchestrator:
    return Orchestrator(
        preprocessing=PreProcess(),
        postprocessing=PostProcess(),
        mip_solution_provider=MipHighsSolutionProvider(),
        heuristic_solution_provider=HeuristicSolutionProvider(),
        enumeration_solution_provider=EnumerationSolutionProvider(),
        # Forced to 0 (never true, since any non-empty feasible-products list
        # has combination_count >= 2) so this file's fixtures deterministically
        # route to MIP, which is what test__solve__given_output_dir__... needs
        # (it asserts model.lp exists, which only MipHighsSolutionProvider writes).
        max_combinations_for_enumeration=0,
    )


@pytest.fixture
def banana() -> Product:
    return Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)


def test__solve__given_unknown_request_id__returns_failure_response():
    # ARRANGE
    use_case = SolveSingleRequest(request_loader=_FakeDataLoader(None), orchestrator=_orchestrator())

    # ACT
    response = use_case.solve("missing")

    # ASSERT
    assert response.status == "FAILURE"
    assert response.recommendation is None
    assert "missing" in (response.message or "")


def test__solve__given_solvable_request__returns_success_response(banana):
    # ARRANGE
    request = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana])
    use_case = SolveSingleRequest(request_loader=_FakeDataLoader(request), orchestrator=_orchestrator())

    # ACT
    response = use_case.solve("1")

    # ASSERT
    assert response.status == "SUCCESS"
    assert response.recommendation is not None


def test__solve__given_output_dir__forwards_it_to_the_orchestrator(banana, tmp_path):
    # ARRANGE — _orchestrator() forces enumeration off, so this routes to
    # MipHighsSolutionProvider, which writes model.lp into output_dir when given one.
    request = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana])
    use_case = SolveSingleRequest(request_loader=_FakeDataLoader(request), orchestrator=_orchestrator())

    # ACT
    use_case.solve("1", output_dir=tmp_path)

    # ASSERT
    assert (Path(tmp_path) / "model.lp").exists()
