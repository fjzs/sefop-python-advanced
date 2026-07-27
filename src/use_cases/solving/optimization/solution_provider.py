"""
ROLE: Abstract Base Class — contract that every solution provider must follow.

WHY THIS EXISTS:
    Solution providers (MIP solver, greedy heuristic, brute-force enumeration,
    etc.) are pluggable implementations of this interface so Orchestrator can
    select and run any of them through a single ``solve()`` call without knowing
    which one it picked.

    This is an internal solving-pipeline contract, not a public port: it lives
    inside use_cases/solving/ because only the solving pipeline's own
    collaborators (Orchestrator, MipHighsSolutionProvider, MipGoogleScipSolutionProvider,
    HeuristicSolutionProvider, EnumerationSolutionProvider) ever implement or call it —
    it is not something adapters/ or startup.py wire in from the outside the way
    use_cases/ports/ contracts are.

WHERE IMPLEMENTATIONS LIVE:
    src/use_cases/solving/optimization/<technology>/, e.g. mip_highs/mip_highs_solution_provider.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from domain.recommendation import Recommendation
from use_cases.solving.preprocessing.pre_processed_data import PreProcessedData


class SolutionProvider(ABC):
    """
    An abstract base class (ABC) is like a contract: it declares a set of
    methods that every provider **must** implement, but says nothing about
    *how*. Any class that inherits from ``SolutionProvider`` is forced to
    provide ``solve()`` and ``name``, so Orchestrator can call ``solve()``
    and log which one it picked, without caring whether an exact MIP solver,
    a greedy heuristic, or brute-force enumeration is doing the work behind
    the scenes.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-friendly label for this provider, used in Orchestrator's selection log.

        Returns:
            A short technology label, e.g. "MIP (HiGHS)" or "Greedy Heuristic".
        """

    @abstractmethod
    def solve(self, data: PreProcessedData, output_dir: Path | None = None) -> Recommendation | None:
        """Solve the optimization problem for the given data.

        Args:
            data: The preprocessed knapsack request and related context.
            output_dir: Directory to write solver debugging artifacts into,
                or None to skip writing any. Providers that produce no such
                artifacts (e.g. the greedy heuristic) simply ignore this.

        Returns:
            The provider's best Recommendation, or None if no feasible
            solution exists. Providers do not currently surface multiple
            candidate solutions or ties.
        """
