"""HTTP routes for the web delivery mechanism: POST /solve, GET /health.

WHY THIS EXISTS:
    This module is the outermost ring (Frameworks & Drivers): it knows about
    FastAPI and Pydantic, and nothing from domain/ or use_cases/ directly.
    Each route's job is only to: build this request's dependencies via
    startup.py (the composition root), hand off to the controller, and
    return whatever the presenter produces for FastAPI to serialize.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

import startup
from adapters.web import controller, presenter
from frameworks_and_drivers.web.schemas import SolveRequestSchema, SolveResponseSchema

router = APIRouter()

# Built once at import time, not per-request: solver_name only changes if the
# SOLVER_NAME environment variable changes, which never happens mid-process.
_settings = startup.WebSettings()


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness check the Docker image's CI smoke test polls after startup."""
    return {"status": "ok"}


@router.post("/solve", response_model=SolveResponseSchema)
def solve(payload: SolveRequestSchema) -> dict[str, Any]:
    """Solve one knapsack request submitted from the frontend form.

    Defined as a plain `def`, not `async def`: Starlette then runs this in a
    worker thread automatically, so the CPU-bound solver call (HiGHS or
    OR-Tools, both synchronous) never blocks the event loop that serves every
    other connection, including the static frontend files.
    """
    # A fresh loader (and the use case wired to it) per call, never reused
    # across requests — see adapters/web/in_memory_data_loader.py.
    data_loader = startup.build_in_memory_data_loader()
    solve_single_request = startup.build_web_solve_single_request(_settings, data_loader)

    response = controller.handle_solve(payload.model_dump(by_alias=False), data_loader, solve_single_request)
    return presenter.present_solve_response(response)
