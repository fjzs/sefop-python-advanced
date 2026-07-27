from datetime import datetime

import pytest

from domain.product import Product
from domain.recommendation import Recommendation
from domain.request import Request
from use_cases.optimization_response import OptimizationResponse


@pytest.fixture
def banana() -> Product:
    return Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)


@pytest.fixture
def request_(banana) -> Request:
    return Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana])


@pytest.fixture
def recommendation(request_, banana) -> Recommendation:
    return Recommendation(request=request_, quantities={banana: 1})


def test__optimization_response__success__sets_status_and_recommendation(recommendation):
    # ACT
    response = OptimizationResponse.success(recommendation)

    # ASSERT
    assert response.status == "SUCCESS"
    assert response.recommendation is recommendation
    assert response.message is None


def test__optimization_response__failure__sets_status_and_message():
    # ACT
    response = OptimizationResponse.failure("solver timed out")

    # ASSERT
    assert response.status == "FAILURE"
    assert response.recommendation is None
    assert response.message == "solver timed out"


def test__optimization_response__success__given_explicit_timestamp__uses_it_verbatim(recommendation):
    # ARRANGE — callers that need the response's folder to match a folder
    # already created earlier in the run (e.g. cli.py) must be able to pin
    # the timestamp instead of getting a fresh datetime.now().
    fixed_timestamp = datetime(2026, 1, 1, 12, 0, 0)

    # ACT
    response = OptimizationResponse.success(recommendation, timestamp=fixed_timestamp)

    # ASSERT
    assert response.timestamp == fixed_timestamp


def test__optimization_response__failure__given_explicit_timestamp__uses_it_verbatim():
    # ARRANGE
    fixed_timestamp = datetime(2026, 1, 1, 12, 0, 0)

    # ACT
    response = OptimizationResponse.failure("solver timed out", timestamp=fixed_timestamp)

    # ASSERT
    assert response.timestamp == fixed_timestamp
