"""Orchestrates the full "solve a knapsack request" use case.

This is the application-layer entry point that calling code (cli.py, or
SolveMultipleRequests) uses to run one optimization. It coordinates loading
data and running the solving pipeline, so callers don't need to manage those
steps themselves.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from use_cases.optimization_response import OptimizationResponse
from use_cases.ports.base_data_loader import BaseDataLoader
from use_cases.solving.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


class SolveSingleRequest:
    """Runs the "load -> optimize -> respond" pipeline for one request.

    Both collaborators are constructor-injected (Dependency Injection): this
    class only coordinates them, it never builds its own BaseDataLoader or
    Orchestrator. That keeps this use case free to work with any data source
    or solving pipeline the caller (startup.py) assembles, and lets tests
    substitute either one without touching this class.
    """

    def __init__(self, request_loader: BaseDataLoader, orchestrator: Orchestrator) -> None:
        self._request_loader = request_loader
        self._orchestrator = orchestrator

    def solve(
        self, request_id: str, output_dir: Path | None = None, timestamp: datetime | None = None
    ) -> OptimizationResponse:
        """Load a request and run the optimization pipeline.

        Args:
            request_id: Identifier of the request to solve.
            output_dir: Directory to write solver debugging artifacts into,
                or None to skip writing any. This use case has no opinion on
                where that directory lives — the caller (cli.py) resolves it
                from Settings so this layer stays free of output-folder concerns.
            timestamp: When this run started. Stamped onto the returned
                response so the caller can later derive the same output
                folder it computed output_dir from. Defaults to now.

        Returns:
            An OptimizationResponse with the recommendation or an error message.
        """
        logger.info("Solving request: %s", request_id)

        request = self._request_loader.load(request_id)
        if request is None:
            logger.warning("Request not found: %s", request_id)
            return OptimizationResponse.failure(f"Request '{request_id}' not found", timestamp=timestamp)

        recommendation = self._orchestrator.solve(request, output_dir)
        if recommendation is None:
            logger.warning("No feasible solution for request: %s", request_id)
            return OptimizationResponse.failure("No feasible solution found", timestamp=timestamp)

        logger.info("--------- Request %s solved successfully ---------", request_id)
        return OptimizationResponse.success(recommendation, timestamp=timestamp)
