"""End-to-end tests for the web app's HTTP surface, driven through FastAPI's TestClient.

Marked integration (not a real network call, no browser — TestClient drives
the ASGI app in-process — but it exercises the real solve pipeline end to
end, same rationale as tests/integration/'s CLI tests).
"""

import pytest
from fastapi.testclient import TestClient

from frameworks_and_drivers.web.main import app

client = TestClient(app)


@pytest.mark.integration
def test__health__returns_ok():
    # ACT
    response = client.get("/health")

    # ASSERT
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.integration
def test__solve__given_feasible_request__returns_success_with_recommendation():
    # ARRANGE
    payload = {
        "maxWeightKg": 1.0,
        "maxBudgetUsd": 5.0,
        "products": [{"name": "banana", "priceUsd": 1.00, "weightKg": 0.50, "calories": 100}],
    }

    # ACT
    response = client.post("/solve", json=payload)

    # ASSERT
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SUCCESS"
    assert body["recommendation"]["items"][0]["name"] == "banana"


@pytest.mark.integration
def test__solve__given_infeasible_request__returns_failure_status_with_http_200():
    # ARRANGE — the only product costs more than the entire budget.
    payload = {
        "maxWeightKg": 1.0,
        "maxBudgetUsd": 1.0,
        "products": [{"name": "caviar", "priceUsd": 100.0, "weightKg": 0.1, "calories": 10}],
    }

    # ACT
    response = client.post("/solve", json=payload)

    # ASSERT — infeasible is a normal 200 FAILURE response, not an HTTP error
    # (see adapters/web/controller.py's error-handling design).
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILURE"
    assert body["recommendation"] is None


@pytest.mark.integration
def test__solve__given_negative_budget__returns_422():
    # ARRANGE — Field(gt=0) on SolveRequestSchema.max_budget_usd rejects this
    # before the controller ever runs.
    payload = {
        "maxWeightKg": 1.0,
        "maxBudgetUsd": -5.0,
        "products": [{"name": "banana", "priceUsd": 1.00, "weightKg": 0.50, "calories": 100}],
    }

    # ACT
    response = client.post("/solve", json=payload)

    # ASSERT
    assert response.status_code == 422


@pytest.mark.integration
def test__solve__given_empty_products__returns_422():
    # ARRANGE — Field(min_length=1) on SolveRequestSchema.products.
    payload = {"maxWeightKg": 1.0, "maxBudgetUsd": 5.0, "products": []}

    # ACT
    response = client.post("/solve", json=payload)

    # ASSERT
    assert response.status_code == 422
