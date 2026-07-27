"""
ROLE: Value Object — a validated solution to a Request.

WHY THIS EXISTS:
    A Recommendation pairs a chosen quantity per product with the Request it answers, and
    derives the resulting totals itself. Deriving the totals here - rather than trusting a
    caller to compute and pass them in - means a Recommendation can never report totals that
    disagree with its own quantities, and can never exist in a state that violates the
    originating Request's budget or weight limits.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from domain.product import Product
from domain.request import Request


@dataclass(frozen=True)
class Recommendation:
    """A candidate solution to a Request: how many units of each product to take.

    This is a frozen (immutable) value object whose total_calories, total_cost_usd, and
    total_weight_kg fields are *computed*, not supplied by the caller. They are declared with
    ``field(init=False)`` so the constructor signature only accepts request and quantities;
    __post_init__ then derives the totals from those two inputs and uses
    ``object.__setattr__`` to set them - the one sanctioned way to assign a field on a frozen
    dataclass, needed because frozen dataclasses forbid ``self.attr = value`` after
    construction. The same __post_init__ call also re-checks the totals against the Request's
    budget and weight limits, so a Recommendation that is over budget or over weight can never
    be constructed in the first place.

    Attributes:
        request: The Request this recommendation answers.
        quantities: Number of units to take of each product. Every key must be a product
            from request.products, and every value must be >= 1.
        total_calories: Sum of calories across all selected products, derived automatically.
        total_cost_usd: Sum of cost across all selected products, derived automatically.
            Must not exceed request.max_budget_usd.
        total_weight_kg: Sum of weight across all selected products, derived automatically.
            Must not exceed request.max_weight_kg.
    """

    request: Request
    quantities: dict[Product, int]
    total_calories: int = field(init=False)
    total_cost_usd: float = field(init=False)
    total_weight_kg: float = field(init=False)

    def __post_init__(self) -> None:
        if not self.quantities:
            raise ValueError("quantities must be non-empty")
        allowed = set(self.request.products)
        for product, qty in self.quantities.items():
            if product not in allowed:
                raise ValueError(f"product '{product.name}' is not in request")
            if qty < 1:
                raise ValueError(f"quantity for '{product.name}' must be >= 1")
        calories = sum(p.calories * q for p, q in self.quantities.items())
        cost = sum(p.price_usd * q for p, q in self.quantities.items())
        weight = sum(p.weight_kg * q for p, q in self.quantities.items())
        # object.__setattr__ bypasses the frozen dataclass's usual "no attribute assignment"
        # restriction. This is safe only here, inside __post_init__, before the instance is
        # ever exposed to callers.
        object.__setattr__(self, "total_calories", calories)
        object.__setattr__(self, "total_cost_usd", cost)
        object.__setattr__(self, "total_weight_kg", weight)
        # Re-validate against the originating Request's limits so a Recommendation that
        # overspends the budget or exceeds the weight limit can never exist.
        if cost > self.request.max_budget_usd:
            raise ValueError(f"total cost {cost} exceeds budget {self.request.max_budget_usd}")
        if weight > self.request.max_weight_kg:
            raise ValueError(f"total weight {weight} exceeds limit {self.request.max_weight_kg}")
