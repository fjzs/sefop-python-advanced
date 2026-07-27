"""
ROLE: Value Object — one knapsack problem instance to solve.

WHY THIS EXISTS:
    A Request bundles everything a SolutionProvider needs to run - the budget, the weight
    limit, and the pool of candidate products - into a single, validated unit. Downstream code
    (use_cases, solving providers) can accept a Request without re-checking its contents,
    because an invalid Request can never be constructed in the first place.
"""

from __future__ import annotations
from dataclasses import dataclass
from domain.product import Product


@dataclass(frozen=True)
class Request:
    """One instance of the knapsack problem: pick products within a weight and budget limit.

    This is a frozen (immutable) value object: its identity comes from its data, not from
    object identity, and it cannot be changed after construction. Constructing a Request runs
    all validation immediately, so any code that later receives a Request instance can trust
    that its limits are positive and its product list is well-formed, without re-validating.

    Attributes:
        max_weight_kg: Maximum total weight of selected products, in kilograms.
        max_budget_usd: Maximum total cost of selected products, in US dollars.
        products: Non-empty list of candidate products to choose from. Names must be unique
            within the list, since Product.name is used to identify products in results.
    """

    max_weight_kg: float
    max_budget_usd: float
    products: list[Product]

    def __post_init__(self) -> None:
        if self.max_weight_kg <= 0:
            raise ValueError("max_weight_kg must be > 0")
        if self.max_budget_usd <= 0:
            raise ValueError("max_budget_usd must be > 0")
        if not self.products:
            raise ValueError("products must be a non-empty list")
        names = [p.name for p in self.products]
        # Duplicate names would make a product ambiguous in any report or lookup keyed by
        # name, so this is rejected here rather than left for downstream code to discover.
        if len(names) != len(set(names)):
            raise ValueError("duplicate product names are not allowed")
