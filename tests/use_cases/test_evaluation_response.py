import math

import pytest

from domain.product import Product
from domain.recommendation import Recommendation
from domain.request import Request
from use_cases.evaluation_response import EvaluationResponse


@pytest.fixture
def banana() -> Product:
    return Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)


@pytest.fixture
def recommendation(banana) -> Recommendation:
    request = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana])
    return Recommendation(request=request, quantities={banana: 2})


def test__evaluation_response__success__sets_feasible_and_totals(recommendation):
    # ACT
    response = EvaluationResponse.success(recommendation)

    # ASSERT
    assert response.feasible is True
    assert response.total_calories == recommendation.total_calories
    assert math.isclose(response.total_cost_usd, recommendation.total_cost_usd)
    assert math.isclose(response.total_weight_kg, recommendation.total_weight_kg)
    assert response.message is None


def test__evaluation_response__failure__sets_infeasible_and_message():
    # ACT
    response = EvaluationResponse.failure("total cost exceeds budget")

    # ASSERT
    assert response.feasible is False
    assert response.total_calories is None
    assert response.total_cost_usd is None
    assert response.total_weight_kg is None
    assert response.message == "total cost exceeds budget"
