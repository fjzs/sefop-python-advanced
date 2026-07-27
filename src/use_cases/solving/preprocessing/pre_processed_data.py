"""Data container that carries request data into a SolutionProvider.

Defines the boundary between the preprocessing stage and the SolutionProvider
stage. Keeping them separate makes each independently extensible.
"""

from __future__ import annotations
from dataclasses import dataclass
from domain.product import Product
from domain.request import Request


@dataclass(frozen=True)
class PreProcessedData:
    """Preprocessed data ready for a SolutionProvider to run on.

    Attributes:
        request: The original knapsack request.
        feasible_products: Products where a single unit fits within both the
            weight and budget constraints. SolutionProvider implementations
            should iterate this list instead of request.products to avoid
            wasting effort on products that can never be selected.
    """

    request: Request
    feasible_products: list[Product]
