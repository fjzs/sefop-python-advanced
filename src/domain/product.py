"""
ROLE: Entity — an item the knapsack optimization can select.

WHY THIS EXISTS:
    Product has no dependencies on any other layer (use_cases, adapters, solving). Keeping it
    dependency-free means every other layer can depend on Product without risking a circular
    import, and the entity can be tested or reused in isolation from the rest of the framework.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    """A candidate item for the knapsack problem, with its cost, weight, and nutritional value.

    This is a frozen (immutable) dataclass: once created, a Product cannot be modified.
    Immutability matters here because Product instances are used as dictionary keys elsewhere
    in the domain (see Recommendation.quantities) - a mutable key could change its hash after
    insertion and silently corrupt that dictionary. Validation runs once, in __post_init__,
    so an invalid Product can never exist; callers never need to re-check these fields later.

    Attributes:
        name: Unique, human-readable identifier for the product.
        price_usd: Unit price in US dollars. Must be strictly positive.
        weight_kg: Unit weight in kilograms. Must be strictly positive.
        calories: Nutritional value per unit. Must be strictly positive.
    """

    name: str
    price_usd: float
    weight_kg: float
    calories: int

    def __post_init__(self) -> None:
        # Fail fast: reject an invalid Product at construction time rather than letting
        # a zero-price or zero-weight item silently distort optimization results later.
        if not self.name:
            raise ValueError("name must be a non-empty string")
        if self.price_usd <= 0:
            raise ValueError("price_usd must be > 0")
        if self.weight_kg <= 0:
            raise ValueError("weight_kg must be > 0")
        if self.calories <= 0:
            raise ValueError("calories must be > 0")
