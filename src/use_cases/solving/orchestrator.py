"""
ROLE: Orchestrator — sequences the knapsack optimization pipeline end-to-end.

WHY THIS EXISTS:
    The Orchestrator is the public face of the solve use cases' internal solving
    pipeline (this whole `solving/` subpackage is an implementation detail of
    `SolveSingleRequest`, not a top-level architecture layer). Given a Request, it
    runs three explicit stages: preprocessing -> provider selection and solving ->
    postprocessing. Returns a Recommendation or None. Callers never need to know
    which provider was chosen or how preprocessing/postprocessing work.

    Key design: provider selection is based on problem size. A small enough
    combinatorial search space (at most max_combinations_for_enumeration) is
    solved exactly by brute force; otherwise, small enough problems (at most
    max_products_for_mip products) use the exact MIP solver; anything larger
    uses the fast greedy heuristic. This selection is hidden from callers.
"""

from __future__ import annotations

import logging
from pathlib import Path

from domain.recommendation import Recommendation
from domain.request import Request
from use_cases.solving.optimization.enumeration.enumeration_solution_provider import combination_count
from use_cases.solving.optimization.solution_provider import SolutionProvider
from use_cases.solving.postprocessing.postprocessing import PostProcess
from use_cases.solving.preprocessing.pre_processed_data import PreProcessedData
from use_cases.solving.preprocessing.preprocessing import PreProcess

logger = logging.getLogger(__name__)


class Orchestrator:
    """Selects and runs the appropriate solution provider for a Request.

    The Orchestrator is not itself a provider, it coordinates the available
    providers. Callers give the Orchestrator a request, and it silently
    picks the right one based on problem size. Every collaborator
    (preprocessing, postprocessing, and all three providers) is
    constructor-injected (Dependency Injection) rather than built here, so a
    fork can swap any stage — or test this class with fakes — without
    editing this file. In particular, Orchestrator only ever sees the
    abstract SolutionProvider type: it has no idea which MIP solver
    technology (or future technology) is behind mip_solution_provider.
    """

    def __init__(
        self,
        preprocessing: PreProcess,
        postprocessing: PostProcess,
        mip_solution_provider: SolutionProvider,
        heuristic_solution_provider: SolutionProvider,
        enumeration_solution_provider: SolutionProvider,
        max_products_for_mip: int = 50,
        max_combinations_for_enumeration: int = 1000,
    ) -> None:
        self._preprocessing = preprocessing
        self._postprocessing = postprocessing
        self._mip_solution_provider = mip_solution_provider
        self._heuristic_solution_provider = heuristic_solution_provider
        self._enumeration_solution_provider = enumeration_solution_provider
        # Problems with at most this many products are solved with MIP
        # (exact). Larger problems are routed to the greedy heuristic for
        # speed. A constructor default, not global Settings: this threshold
        # is an implementation detail of how the Orchestrator picks a
        # provider, not something a data scientist configures per run.
        self._max_products_for_mip = max_products_for_mip
        # Problems whose combinatorial search space is at most this large are
        # solved exactly by brute-force enumeration instead of invoking a
        # solver at all. Same rationale as max_products_for_mip: an
        # implementation detail, not global Settings.
        self._max_combinations_for_enumeration = max_combinations_for_enumeration

    def solve(self, request: Request, output_dir: Path | None = None) -> Recommendation | None:
        """Run the full optimization pipeline.

        Args:
            request: The knapsack request to solve.
            output_dir: Directory to write solver debugging artifacts into,
                or None to skip writing any. Forwarded to whichever provider
                is selected; ignored by providers that produce none.

        Returns:
            The best Recommendation found, or None if no feasible solution exists.
        """
        data = self._preprocessing.run(request)
        if not data.feasible_products:
            # Every product costs more than the budget or weighs more than the
            # capacity, so no valid selection exists.
            logger.warning("No feasible products after preprocessing; skipping solve")
            return None
        provider = self._select_provider(data)
        logger.info("Selected provider: %s", provider.name)
        recommendation = provider.solve(data, output_dir)
        if recommendation is None:
            return None
        return self._postprocessing.run(recommendation)

    def _select_provider(self, data: PreProcessedData) -> SolutionProvider:
        """Choose enumeration, MIP, or the greedy heuristic based on problem size.

        Enumeration is tried first: it is exact, and for a small enough
        combination space it's simpler (and just as fast) as invoking an
        external solver. MIP is the fallback exact method for problems too
        large to brute-force but still small enough to solve exactly in
        reasonable time. Anything larger falls back to the heuristic.

        Using feasible_products (not request.products) reflects the actual
        problem size after preprocessing: infeasible products were already
        removed and will not appear in the model.

        Args:
            data: The preprocessed data to evaluate.

        Returns:
            The provider instance to use.
        """
        if combination_count(data) <= self._max_combinations_for_enumeration:
            return self._enumeration_solution_provider
        if len(data.feasible_products) <= self._max_products_for_mip:
            return self._mip_solution_provider
        return self._heuristic_solution_provider
