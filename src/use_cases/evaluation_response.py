"""
ROLE: Value Object — packages a feasibility-evaluation result (or error) for callers.

WHY THIS EXISTS:
    Every call to EvaluateSolutionForRequest returns an ``EvaluationResponse``
    rather than a raw ``Recommendation``. This gives callers a uniform object to
    inspect: check ``feasible``, read the totals on success, or read ``message``
    on failure — no exception handling required.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.recommendation import Recommendation


@dataclass(frozen=True)
class EvaluationResponse:
    """Output of the "evaluate a candidate solution" use case.

    Attributes:
        feasible: Whether the candidate quantities satisfy the request's
            budget and weight limits.
        total_calories: Sum of calories across the candidate quantities, or
            None when infeasible.
        total_cost_usd: Sum of cost across the candidate quantities, or None
            when infeasible.
        total_weight_kg: Sum of weight across the candidate quantities, or
            None when infeasible.
        message: Explanation of why the candidate could not be evaluated or
            is infeasible, None on success.
    """

    feasible: bool
    total_calories: int | None
    total_cost_usd: float | None
    total_weight_kg: float | None
    message: str | None

    @classmethod
    def success(cls, recommendation: Recommendation) -> "EvaluationResponse":
        """Build a feasible response from an already-validated Recommendation.

        Args:
            recommendation: The Recommendation built from the candidate
                quantities. Its totals are trusted as-is because
                Recommendation.__post_init__ already validated them against
                the originating Request's budget and weight limits.

        Returns:
            An EvaluationResponse with feasible=True and the recommendation's totals.
        """
        return cls(
            feasible=True,
            total_calories=recommendation.total_calories,
            total_cost_usd=recommendation.total_cost_usd,
            total_weight_kg=recommendation.total_weight_kg,
            message=None,
        )

    @classmethod
    def failure(cls, message: str) -> "EvaluationResponse":
        """Build an infeasible (or invalid) response with an error description.

        Args:
            message: Human-readable explanation of why the candidate could
                not be evaluated or does not fit the request's constraints.

        Returns:
            An EvaluationResponse with feasible=False and no totals.
        """
        return cls(
            feasible=False,
            total_calories=None,
            total_cost_usd=None,
            total_weight_kg=None,
            message=message,
        )
