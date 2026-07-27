"""
ROLE: Value Object — packages an optimization result (or error) for callers.

WHY THIS EXISTS:
    Every call to a solve use case returns an ``OptimizationResponse`` rather
    than a raw ``Recommendation``. This gives callers a uniform object to
    inspect: check ``status``, read the ``recommendation`` on success, or read
    the ``message`` on failure — no exception handling required.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.recommendation import Recommendation


@dataclass(frozen=True)
class OptimizationResponse:
    """Output of the "solve a request" use cases.

    Attributes:
        recommendation: The knapsack recommendation, or None on failure.
        status: "SUCCESS" or "FAILURE".
        timestamp: When this run started. Callers that need the on-disk
            output folder to be predictable (e.g. cli.py, which creates that
            folder before solving even begins) pin this value explicitly
            rather than letting it default to the moment the response object
            happens to be built.
        message: Error description on failure, None on success.
    """

    recommendation: Recommendation | None
    status: str
    timestamp: datetime
    message: str | None

    @classmethod
    def success(cls, recommendation: Recommendation, timestamp: datetime | None = None) -> "OptimizationResponse":
        """Build a successful response wrapping the given recommendation.

        Args:
            recommendation: The optimization result to return.
            timestamp: When this run started. Defaults to now if the caller
                has no earlier timestamp to reuse.

        Returns:
            An OptimizationResponse with status "SUCCESS".
        """
        return cls(
            recommendation=recommendation,
            status="SUCCESS",
            timestamp=timestamp if timestamp is not None else datetime.now(),
            message=None,
        )

    @classmethod
    def failure(cls, message: str, timestamp: datetime | None = None) -> "OptimizationResponse":
        """Build a failure response with an error description.

        Args:
            message: Human-readable explanation of what went wrong.
            timestamp: When this run started. Defaults to now if the caller
                has no earlier timestamp to reuse.

        Returns:
            An OptimizationResponse with status "FAILURE" and no recommendation.
        """
        return cls(
            recommendation=None,
            status="FAILURE",
            timestamp=timestamp if timestamp is not None else datetime.now(),
            message=message,
        )
