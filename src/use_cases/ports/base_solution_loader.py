"""
ROLE: Abstract Base Class — contract for loading a candidate solution to evaluate.

WHY THIS EXISTS:
    EvaluateSolutionForRequest needs to read a user-supplied candidate
    solution (which products, and how many of each) without caring whether
    that solution is stored as JSON, CSV, or something else. This base class
    declares the one method any solution-loading strategy must provide.

WHERE IMPLEMENTATIONS LIVE:
    Concrete loaders live in src/adapters/, e.g. json_solution_loader.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseSolutionLoader(ABC):
    """
    This is an abstract base class (ABC) - a contract pattern: it declares
    the one method every solution-loading strategy must provide, without
    dictating the file format. Any class that inherits from
    BaseSolutionLoader must provide a ``load()`` method, so
    EvaluateSolutionForRequest can read a candidate solution without caring
    whether it comes from a JSON file or something else.

    Deliberately returns product **names**, not domain Product instances:
    matching a name to a Product on a specific Request is the use case's job,
    since only the use case knows which Request the candidate answers.
    """

    @abstractmethod
    def load(self, path: Path) -> dict[str, int] | None:
        """Load candidate product quantities from a file.

        Args:
            path: Path to the file describing the candidate solution.

        Returns:
            Mapping from product name to the candidate quantity selected, or
            None if the file does not exist.

        Raises:
            ValueError: If the file exists but is malformed or contains a
                non-positive quantity.
        """
