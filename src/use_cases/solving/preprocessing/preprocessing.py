"""Preprocessing stage that prepares request data for a SolutionProvider.

Domain validation (Request.__post_init__) already guarantees that each product
has positive weight, price, and calories and that names are unique. Preprocessing
goes one step further: it removes products that can never appear in any solution.

A product is *individually infeasible* if a single unit of it already exceeds
either the weight capacity or the budget. No SolutionProvider — exact or
heuristic — could ever select such a product, so filtering them out here
shrinks the problem before any solver sees it.
"""

from __future__ import annotations

from domain.request import Request
from use_cases.solving.preprocessing.pre_processed_data import PreProcessedData


class PreProcess:
    """Preprocessing step before a SolutionProvider runs.

    Filters out products that are individually infeasible, then wraps the
    remaining data in PreProcessedData for the SolutionProvider stage.
    """

    def run(self, request: Request) -> PreProcessedData:
        """Filter infeasible products and prepare data for the SolutionProvider stage.

        A product is infeasible when a single unit costs more than the total
        budget or weighs more than the total weight capacity — it can never
        be included in any valid solution.

        Args:
            request: The validated knapsack request.

        Returns:
            PreProcessedData with feasible_products containing only the
            products that can physically fit within the constraints.
        """
        feasible_products = [
            p
            for p in request.products
            if p.price_usd <= request.max_budget_usd and p.weight_kg <= request.max_weight_kg
        ]
        return PreProcessedData(request=request, feasible_products=feasible_products)
