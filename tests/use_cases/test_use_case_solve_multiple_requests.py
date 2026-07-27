from datetime import datetime
from pathlib import Path

import pytest

from domain.product import Product
from domain.request import Request
from use_cases.ports.base_data_loader import BaseDataLoader
from use_cases.ports.base_request_discovery import BaseRequestDiscovery
from use_cases.solving.optimization.enumeration.enumeration_solution_provider import EnumerationSolutionProvider
from use_cases.solving.optimization.heuristic.heuristic_solution_provider import HeuristicSolutionProvider
from use_cases.solving.optimization.mip_highs.mip_highs_solution_provider import MipHighsSolutionProvider
from use_cases.solving.orchestrator import Orchestrator
from use_cases.solving.postprocessing.postprocessing import PostProcess
from use_cases.solving.preprocessing.preprocessing import PreProcess
from use_cases.use_case_solve_multiple_requests import SolveMultipleRequests
from use_cases.use_case_solve_single_request import SolveSingleRequest


class _FakeDiscovery(BaseRequestDiscovery):
    def __init__(self, ids: list[str]) -> None:
        self._ids = ids

    def list_ids(self) -> list[str]:
        return self._ids


class _FakeDataLoader(BaseDataLoader):
    def __init__(self, requests_by_id: dict[str, Request]) -> None:
        self._requests_by_id = requests_by_id

    def load(self, request_id: str) -> Request | None:
        return self._requests_by_id.get(request_id)


def _orchestrator() -> Orchestrator:
    return Orchestrator(
        preprocessing=PreProcess(),
        postprocessing=PostProcess(),
        mip_solution_provider=MipHighsSolutionProvider(),
        heuristic_solution_provider=HeuristicSolutionProvider(),
        enumeration_solution_provider=EnumerationSolutionProvider(),
    )


@pytest.fixture
def banana() -> Product:
    return Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)


def test__solve_all__solves_every_discovered_id_and_returns_responses_in_order(banana):
    # ARRANGE
    requests = {
        "1": Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana]),
        "2": Request(max_weight_kg=5.0, max_budget_usd=0.01, products=[banana]),  # infeasible
    }
    solve_single_request = SolveSingleRequest(request_loader=_FakeDataLoader(requests), orchestrator=_orchestrator())
    use_case = SolveMultipleRequests(
        request_discovery=_FakeDiscovery(["1", "2"]), solve_single_request=solve_single_request
    )

    # ACT
    responses = use_case.solve_all(Path("unused"))

    # ASSERT
    assert len(responses) == 2
    assert responses[0].status == "SUCCESS"
    assert responses[1].status == "FAILURE"


def test__solve_all__given_no_discovered_ids__returns_empty_list(banana):
    # ARRANGE
    solve_single_request = SolveSingleRequest(request_loader=_FakeDataLoader({}), orchestrator=_orchestrator())
    use_case = SolveMultipleRequests(request_discovery=_FakeDiscovery([]), solve_single_request=solve_single_request)

    # ACT / ASSERT
    assert use_case.solve_all(Path("unused")) == []


def test__solve_all__shares_one_timestamp_across_the_batch(banana):
    # ARRANGE
    requests = {"1": Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana])}
    solve_single_request = SolveSingleRequest(request_loader=_FakeDataLoader(requests), orchestrator=_orchestrator())
    use_case = SolveMultipleRequests(request_discovery=_FakeDiscovery(["1"]), solve_single_request=solve_single_request)
    fixed_timestamp = datetime(2026, 1, 1, 12, 0, 0)

    # ACT
    responses = use_case.solve_all(Path("unused"), timestamp=fixed_timestamp)

    # ASSERT
    assert responses[0].timestamp == fixed_timestamp
