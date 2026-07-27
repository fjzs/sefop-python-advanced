"""Orchestrates solving every request discovered under a batch folder.

Composes a BaseRequestDiscovery (to find which request IDs exist) with a
SolveSingleRequest (to solve each one), so a whole folder of requests gets
the same "load -> optimize -> respond" behavior as a single solve, without
this use case needing to know how requests are discovered or how one request
gets solved.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from use_cases.optimization_response import OptimizationResponse
from use_cases.ports.base_request_discovery import BaseRequestDiscovery
from use_cases.use_case_solve_single_request import SolveSingleRequest

logger = logging.getLogger(__name__)


class SolveMultipleRequests:
    """Solves every request a BaseRequestDiscovery can find, one at a time.

    Both collaborators are constructor-injected (Dependency Injection).
    Requests are solved sequentially rather than in parallel: this is a
    local console tool run on a data scientist's own machine, so the
    simplicity of a plain loop outweighs any speed gained from threading.
    """

    def __init__(self, request_discovery: BaseRequestDiscovery, solve_single_request: SolveSingleRequest) -> None:
        self._request_discovery = request_discovery
        self._solve_single_request = solve_single_request

    def solve_all(self, output_folder: Path, timestamp: datetime | None = None) -> list[OptimizationResponse]:
        """Solve every discovered request, sharing one timestamp across the batch.

        Args:
            output_folder: Directory under which each solved request gets its
                own subfolder for solver debugging artifacts, so requests in
                the same batch never overwrite each other's artifacts.
            timestamp: When this batch started. Stamped onto every response
                in the batch so a caller writing them to disk later groups
                them under one run. Defaults to now.

        Returns:
            One OptimizationResponse per discovered request, in discovery
            order. This use case never writes to disk itself — persisting
            responses is the caller's job, the same separation SolveSingleRequest
            keeps.
        """
        run_timestamp = timestamp if timestamp is not None else datetime.now()
        request_ids = self._request_discovery.list_ids()
        logger.info("Discovered %d requests to solve", len(request_ids))

        responses = []
        for request_id in request_ids:
            response = self._solve_single_request.solve(
                request_id, output_dir=output_folder / request_id, timestamp=run_timestamp
            )
            responses.append(response)
        return responses
