from typing import Any

from adapters.web.controller import handle_solve
from adapters.web.in_memory_data_loader import InMemoryDataLoader
from use_cases.solving.optimization.enumeration.enumeration_solution_provider import EnumerationSolutionProvider
from use_cases.solving.optimization.heuristic.heuristic_solution_provider import HeuristicSolutionProvider
from use_cases.solving.optimization.mip_highs.mip_highs_solution_provider import MipHighsSolutionProvider
from use_cases.solving.orchestrator import Orchestrator
from use_cases.solving.postprocessing.postprocessing import PostProcess
from use_cases.solving.preprocessing.preprocessing import PreProcess
from use_cases.use_case_solve_single_request import SolveSingleRequest


def _solve_single_request(data_loader: InMemoryDataLoader) -> SolveSingleRequest:
    orchestrator = Orchestrator(
        preprocessing=PreProcess(),
        postprocessing=PostProcess(),
        mip_solution_provider=MipHighsSolutionProvider(),
        heuristic_solution_provider=HeuristicSolutionProvider(),
        enumeration_solution_provider=EnumerationSolutionProvider(),
    )
    return SolveSingleRequest(request_loader=data_loader, orchestrator=orchestrator)


def _valid_payload() -> dict[str, Any]:
    return {
        "max_weight_kg": 5.0,
        "max_budget_usd": 10.0,
        "products": [{"name": "banana", "price_usd": 0.5, "weight_kg": 0.12, "calories": 89}],
    }


def test__handle_solve__given_valid_payload__returns_success_response():
    # ARRANGE
    data_loader = InMemoryDataLoader()
    solve_single_request = _solve_single_request(data_loader)

    # ACT
    response = handle_solve(_valid_payload(), data_loader, solve_single_request)

    # ASSERT
    assert response.status == "SUCCESS"
    assert response.recommendation is not None


def test__handle_solve__given_negative_budget__returns_failure_response_instead_of_raising():
    # ARRANGE — max_budget_usd <= 0 is a domain invariant (Request.__post_init__),
    # not something Pydantic's schema-level constraints would catch upstream in
    # this unit test, so this exercises the controller's own ValueError handling.
    payload = _valid_payload()
    payload["max_budget_usd"] = -1.0
    data_loader = InMemoryDataLoader()
    solve_single_request = _solve_single_request(data_loader)

    # ACT
    response = handle_solve(payload, data_loader, solve_single_request)

    # ASSERT
    assert response.status == "FAILURE"
    assert response.recommendation is None
    assert "max_budget_usd" in (response.message or "")


def test__handle_solve__given_duplicate_product_names__returns_failure_response():
    # ARRANGE — duplicate names is a Request-level invariant.
    payload = _valid_payload()
    payload["products"] = payload["products"] * 2
    data_loader = InMemoryDataLoader()
    solve_single_request = _solve_single_request(data_loader)

    # ACT
    response = handle_solve(payload, data_loader, solve_single_request)

    # ASSERT
    assert response.status == "FAILURE"
    assert "duplicate" in (response.message or "")
