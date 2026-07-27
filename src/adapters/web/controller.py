"""Translates a raw solve payload into a SolveSingleRequest call.

WHY THIS EXISTS:
    SolveSingleRequest.solve(request_id, ...) expects a request_id it can
    hand to its injected BaseDataLoader — it has no notion of "a request that
    just arrived over HTTP with no id at all". This controller bridges that
    gap: it builds a domain Request from the already-validated,
    already-framework-agnostic payload the web delivery mechanism hands it,
    stores it in the caller-supplied InMemoryDataLoader under a fresh id, and
    only then calls solve(). It takes no dependency on Pydantic or FastAPI —
    those belong to frameworks_and_drivers/web/, one ring further out; this
    module only ever sees plain Python data (dict, list, str, float, int).
"""

from __future__ import annotations

from typing import Any

from adapters.web.in_memory_data_loader import InMemoryDataLoader
from domain.product import Product
from domain.request import Request
from use_cases.optimization_response import OptimizationResponse
from use_cases.use_case_solve_single_request import SolveSingleRequest


def handle_solve(
    payload: dict[str, Any],
    data_loader: InMemoryDataLoader,
    solve_single_request: SolveSingleRequest,
) -> OptimizationResponse:
    """Build a Request from payload and solve it.

    Args:
        payload: The solve request body, already validated and coerced to
            plain Python types by the web framework — expects
            max_weight_kg, max_budget_usd, and a list of products each with
            name, price_usd, weight_kg, calories.
        data_loader: Where the built Request is stored so solve_single_request
            (constructed against this same instance) can load it back.
        solve_single_request: Pre-wired by the caller, via
            startup.build_web_solve_single_request(), against data_loader.

    Returns:
        The OptimizationResponse from solving, or a FAILURE response if
        payload doesn't satisfy the domain's validation rules (e.g. a
        non-positive budget). Pydantic's field-level constraints catch most
        bad input before this function ever runs, but business invariants
        that live in Product/Request.__post_init__ can't be expressed as
        Pydantic field constraints, so they're caught here instead of
        propagating as an unhandled exception — the same FAILURE shape a
        genuinely infeasible request already uses.
    """
    try:
        request = _build_request(payload)
    except ValueError as exc:
        return OptimizationResponse.failure(str(exc))

    request_id = data_loader.store(request)
    return solve_single_request.solve(request_id)


def _build_request(payload: dict[str, Any]) -> Request:
    """Map the payload dict to a domain Request, letting Product/Request raise ValueError."""
    products = [
        Product(
            name=p["name"],
            price_usd=p["price_usd"],
            weight_kg=p["weight_kg"],
            calories=p["calories"],
        )
        for p in payload["products"]
    ]
    return Request(
        max_weight_kg=payload["max_weight_kg"],
        max_budget_usd=payload["max_budget_usd"],
        products=products,
    )
