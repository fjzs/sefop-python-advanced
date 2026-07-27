import math
from pathlib import Path

import pytest

from domain.product import Product
from domain.request import Request
from use_cases.ports.base_data_loader import BaseDataLoader
from use_cases.ports.base_solution_loader import BaseSolutionLoader
from use_cases.use_case_evaluate_solution_for_request import EvaluateSolutionForRequest


class _FakeDataLoader(BaseDataLoader):
    def __init__(self, request: Request | None) -> None:
        self._request = request

    def load(self, request_id: str) -> Request | None:
        return self._request


class _FakeSolutionLoader(BaseSolutionLoader):
    def __init__(self, quantities: dict[str, int] | None) -> None:
        self._quantities = quantities

    def load(self, path: Path) -> dict[str, int] | None:
        return self._quantities


@pytest.fixture
def banana() -> Product:
    return Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)


@pytest.fixture
def chips() -> Product:
    return Product(name="chips", price_usd=1.0, weight_kg=0.2, calories=150)


@pytest.fixture
def request_(banana, chips) -> Request:
    return Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana, chips])


def test__evaluate__given_unknown_request_id__returns_failure(request_):
    # ARRANGE
    use_case = EvaluateSolutionForRequest(request_loader=_FakeDataLoader(None), solution_loader=_FakeSolutionLoader({}))

    # ACT
    response = use_case.evaluate("missing", Path("solution.json"))

    # ASSERT
    assert response.feasible is False
    assert "missing" in (response.message or "")


def test__evaluate__given_missing_solution_file__returns_failure(request_):
    # ARRANGE — solution_loader returns None to signal "file not found"
    use_case = EvaluateSolutionForRequest(
        request_loader=_FakeDataLoader(request_), solution_loader=_FakeSolutionLoader(None)
    )

    # ACT
    response = use_case.evaluate("1", Path("missing.json"))

    # ASSERT
    assert response.feasible is False
    assert "missing.json" in (response.message or "")


def test__evaluate__given_unknown_product_name__returns_failure(request_):
    # ARRANGE — "truffle" is not in the request's product catalogue
    use_case = EvaluateSolutionForRequest(
        request_loader=_FakeDataLoader(request_), solution_loader=_FakeSolutionLoader({"truffle": 1})
    )

    # ACT
    response = use_case.evaluate("1", Path("solution.json"))

    # ASSERT
    assert response.feasible is False
    assert "truffle" in (response.message or "")


def test__evaluate__given_candidate_over_budget__returns_infeasible(request_, chips):
    # ARRANGE — 20 chips cost $20, over the $10 budget
    use_case = EvaluateSolutionForRequest(
        request_loader=_FakeDataLoader(request_), solution_loader=_FakeSolutionLoader({"chips": 20})
    )

    # ACT
    response = use_case.evaluate("1", Path("solution.json"))

    # ASSERT
    assert response.feasible is False
    assert response.total_cost_usd is None


def test__evaluate__given_candidate_over_weight__returns_infeasible(request_, banana):
    # ARRANGE — banana weighs 0.12 kg; 100 units exceed the 5 kg limit
    use_case = EvaluateSolutionForRequest(
        request_loader=_FakeDataLoader(request_), solution_loader=_FakeSolutionLoader({"banana": 100})
    )

    # ACT
    response = use_case.evaluate("1", Path("solution.json"))

    # ASSERT
    assert response.feasible is False


def test__evaluate__given_feasible_candidate__returns_success_with_totals(request_, banana, chips):
    # ARRANGE — 2 bananas + 1 chips: cost=2.0, weight=0.44kg, calories=328
    use_case = EvaluateSolutionForRequest(
        request_loader=_FakeDataLoader(request_), solution_loader=_FakeSolutionLoader({"banana": 2, "chips": 1})
    )

    # ACT
    response = use_case.evaluate("1", Path("solution.json"))

    # ASSERT
    assert response.feasible is True
    assert response.total_calories == 328
    assert math.isclose(response.total_cost_usd, 2.0)
    assert math.isclose(response.total_weight_kg, 0.44)
