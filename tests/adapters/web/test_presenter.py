import math

from adapters.web.presenter import present_solve_response
from domain.product import Product
from domain.recommendation import Recommendation
from domain.request import Request
from use_cases.optimization_response import OptimizationResponse


def test__present_solve_response__given_failure__returns_failure_dict_with_no_recommendation():
    # ARRANGE
    response = OptimizationResponse.failure("no feasible solution")

    # ACT
    result = present_solve_response(response)

    # ASSERT
    assert result == {"status": "FAILURE", "message": "no feasible solution", "recommendation": None}


def test__present_solve_response__given_success__shapes_items_and_totals():
    # ARRANGE
    banana = Product(name="banana", price_usd=0.5, weight_kg=0.12, calories=89)
    request = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[banana])
    recommendation = Recommendation(request=request, quantities={banana: 3})
    response = OptimizationResponse.success(recommendation)

    # ACT
    result = present_solve_response(response)

    # ASSERT
    assert result["status"] == "SUCCESS"
    assert result["message"] is None
    assert result["recommendation"]["items"] == [
        {"name": "banana", "quantity": 3, "price_usd": 0.5, "weight_kg": 0.12, "calories": 89}
    ]
    assert math.isclose(result["recommendation"]["total_cost_usd"], 1.5)
    assert math.isclose(result["recommendation"]["total_weight_kg"], 0.36)
    assert result["recommendation"]["total_calories"] == 267


def test__present_solve_response__given_multiple_products__sorts_items_by_name():
    # ARRANGE — inserted in reverse alphabetical order to prove sorting, not
    # insertion order, drives the output.
    walnut = Product(name="walnut", price_usd=2.0, weight_kg=0.05, calories=200)
    apple = Product(name="apple", price_usd=1.0, weight_kg=0.2, calories=95)
    request = Request(max_weight_kg=5.0, max_budget_usd=10.0, products=[walnut, apple])
    recommendation = Recommendation(request=request, quantities={walnut: 1, apple: 1})
    response = OptimizationResponse.success(recommendation)

    # ACT
    result = present_solve_response(response)

    # ASSERT
    names = [item["name"] for item in result["recommendation"]["items"]]
    assert names == ["apple", "walnut"]
