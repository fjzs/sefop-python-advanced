"""Orchestrates the "evaluate a candidate solution" use case.

Given a request ID and a path to a candidate solution (product name ->
quantity), checks whether that candidate fits within the request's budget and
weight limits. Unlike SolveSingleRequest, no solver is involved here: this
use case reuses Recommendation's own validation to perform the feasibility
check, rather than reimplementing it.
"""

from __future__ import annotations

import logging
from pathlib import Path

from domain.recommendation import Recommendation
from use_cases.evaluation_response import EvaluationResponse
from use_cases.ports.base_data_loader import BaseDataLoader
from use_cases.ports.base_solution_loader import BaseSolutionLoader

logger = logging.getLogger(__name__)


class EvaluateSolutionForRequest:
    """Checks whether a candidate solution is feasible for a given request.

    Both collaborators are constructor-injected (Dependency Injection). This
    use case builds a Recommendation from the request and the candidate
    quantities and lets Recommendation.__post_init__'s existing budget/weight
    validation perform the feasibility check, instead of duplicating that
    logic here.
    """

    def __init__(self, request_loader: BaseDataLoader, solution_loader: BaseSolutionLoader) -> None:
        self._request_loader = request_loader
        self._solution_loader = solution_loader

    def evaluate(self, request_id: str, solution_path: Path) -> EvaluationResponse:
        """Load a request and a candidate solution, and check feasibility.

        Args:
            request_id: Identifier of the request the candidate answers.
            solution_path: Path to the file describing the candidate quantities.

        Returns:
            An EvaluationResponse reporting feasibility and totals, or an
            explanation of why the candidate could not be evaluated.
        """
        request = self._request_loader.load(request_id)
        if request is None:
            logger.warning("Request not found: %s", request_id)
            return EvaluationResponse.failure(f"Request '{request_id}' not found")

        raw_quantities = self._solution_loader.load(solution_path)
        if raw_quantities is None:
            logger.warning("Solution file not found: %s", solution_path)
            return EvaluationResponse.failure(f"Solution file '{solution_path}' not found")

        # Checked explicitly, with its own message, rather than left for
        # Recommendation to reject: Recommendation's "not in request" error is
        # about feasibility bookkeeping, but an unknown product name here means
        # the candidate solution and the request don't even refer to the same
        # catalogue, which deserves a clearer diagnosis.
        product_by_name = {p.name: p for p in request.products}
        unknown_names = sorted(name for name in raw_quantities if name not in product_by_name)
        if unknown_names:
            return EvaluationResponse.failure(
                f"Solution references product(s) not in request '{request_id}': {', '.join(unknown_names)}"
            )

        quantities = {product_by_name[name]: quantity for name, quantity in raw_quantities.items()}
        try:
            recommendation = Recommendation(request=request, quantities=quantities)
        except ValueError as exc:
            return EvaluationResponse.failure(str(exc))

        return EvaluationResponse.success(recommendation)
