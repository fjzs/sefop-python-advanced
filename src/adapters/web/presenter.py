"""Shapes an OptimizationResponse into plain data for the web delivery mechanism.

WHY THIS EXISTS:
    The web app's HTTP response shouldn't just be OptimizationResponse's
    __dict__ — Recommendation.quantities is a dict[Product, int], and Product
    isn't JSON-serializable, so it needs reshaping into something the
    frameworks_and_drivers/web/ layer can hand to its Pydantic response model.
    This presenter does that reshaping and nothing else: like controller.py,
    it returns plain Python data (dict, list, str, float, int) and takes no
    dependency on Pydantic or FastAPI.
"""

from __future__ import annotations

from typing import Any

from use_cases.optimization_response import OptimizationResponse


def present_solve_response(response: OptimizationResponse) -> dict[str, Any]:
    """Reshape an OptimizationResponse into a plain dict the web layer can serialize.

    Args:
        response: The use case's output to present.

    Returns:
        A dict with "status", "message", and "recommendation" keys.
        "recommendation" is None on failure, otherwise a dict with "items"
        (one entry per selected product: name, quantity, price_usd,
        weight_kg, calories) and the three request-level totals.
    """
    if response.recommendation is None:
        return {"status": response.status, "message": response.message, "recommendation": None}

    recommendation = response.recommendation
    items = [
        {
            "name": product.name,
            "quantity": quantity,
            "price_usd": product.price_usd,
            "weight_kg": product.weight_kg,
            "calories": product.calories,
        }
        # Sorted by name for a stable, human-scannable response — quantities is
        # an ordinary dict with no guaranteed presentation order of its own.
        for product, quantity in sorted(recommendation.quantities.items(), key=lambda pair: pair[0].name)
    ]
    return {
        "status": response.status,
        "message": response.message,
        "recommendation": {
            "items": items,
            "total_cost_usd": recommendation.total_cost_usd,
            "total_weight_kg": recommendation.total_weight_kg,
            "total_calories": recommendation.total_calories,
        },
    }
