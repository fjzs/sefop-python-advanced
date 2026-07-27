"""
ROLE: Implementation — of SolutionProvider, using exhaustive search rather than
any solver library. Brute-force, exact solver used for small search spaces and
as a test oracle.

WHY THIS EXISTS:
    Every combination of per-product quantities is tried; the feasible combination
    with the highest total_calories wins. This is simple enough to trust by
    inspection, which is exactly why it also serves as the ground truth other
    providers (MipHighsSolutionProvider, MipGoogleScipSolutionProvider,
    HeuristicSolutionProvider) are checked against in tests, instead of asserting
    on their internal formulation.
"""

from __future__ import annotations

import itertools
from math import floor
from pathlib import Path

from domain.product import Product
from domain.recommendation import Recommendation
from domain.request import Request
from use_cases.solving.optimization.solution_provider import SolutionProvider
from use_cases.solving.preprocessing.pre_processed_data import PreProcessedData


def _max_quantity(request: Request, product: Product) -> int:
    """Return the most units of product that could ever fit, ignoring every other product.

    This is a deliberately loose (upper) bound: budget and weight are each
    considered alone, not jointly with the rest of the catalogue. It only
    needs to be large enough that the true optimum is never excluded from
    the search space it bounds.
    """
    return floor(min(request.max_budget_usd / product.price_usd, request.max_weight_kg / product.weight_kg))


def combination_count(data: PreProcessedData) -> int:
    """Return the size of the brute-force search space for this data.

    Product of (max_qty_i + 1) across all feasible products. Exposed
    separately from solve() so Orchestrator can decide whether to route to
    enumeration at all without paying for the enumeration itself — this is
    just one multiplication per feasible product, not a search.

    Args:
        data: The preprocessed knapsack request and feasible products.

    Returns:
        Total number of quantity combinations enumeration would need to try.
    """
    count = 1
    for product in data.feasible_products:
        count *= _max_quantity(data.request, product) + 1
    return count


class EnumerationSolutionProvider(SolutionProvider):
    """Tries every combination of product quantities and keeps the best one.

    Feasibility is delegated entirely to Recommendation.__post_init__'s
    existing budget/weight validation rather than reimplemented here: a
    combination is feasible if and only if constructing a Recommendation
    from it doesn't raise ValueError. This keeps the one feasibility check
    in the codebase in one place, instead of two implementations that could
    silently drift apart.
    """

    @property
    def name(self) -> str:
        return "Brute-force Enumeration"

    def solve(self, data: PreProcessedData, output_dir: Path | None = None) -> Recommendation | None:
        """Exhaustively search every product-quantity combination.

        Args:
            data: The preprocessed knapsack data with products and constraints.
            output_dir: Unused. This provider builds no solver model, so it
                has no debugging artifact to write; the parameter exists only
                to satisfy the shared SolutionProvider interface.

        Returns:
            The single best Recommendation found, or None if no combination
            is feasible.
        """
        request = data.request
        products = []
        ranges = []
        for product in data.feasible_products:
            max_qty = _max_quantity(request, product)
            # Unreachable today: preprocessing already guarantees every
            # feasible product's price/weight alone fit the budget/weight
            # limits, which forces max_qty >= 1. Kept as a defensive guard so
            # a future change to that preprocessing invariant can't silently
            # explode this into a zero-width range instead of just skipping
            # the product.
            if max_qty == 0:
                continue
            products.append(product)
            ranges.append(range(max_qty + 1))

        best: Recommendation | None = None
        for combo in itertools.product(*ranges):
            quantities = {product: qty for product, qty in zip(products, combo) if qty >= 1}
            if not quantities:
                continue
            try:
                candidate = Recommendation(request=request, quantities=quantities)
            except ValueError:
                continue
            # Strict '>' (not '>=') means the first-enumerated combination
            # wins any tie, giving deterministic behavior without needing an
            # explicit tie-breaking rule.
            if best is None or candidate.total_calories > best.total_calories:
                best = candidate

        return best
