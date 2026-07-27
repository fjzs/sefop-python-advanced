"""Pydantic request/response models for the HTTP API.

WHY THIS EXISTS:
    These models are the outermost boundary of the web delivery mechanism:
    they validate and type-coerce raw HTTP JSON before anything else runs,
    and they document the API (FastAPI derives the OpenAPI/Swagger schema
    from them automatically). Field constraints here (gt=0, min_length=1)
    catch most malformed input as a standard 422 response before the
    request ever reaches adapters/web/controller.py. Business invariants
    that constraints can't express (e.g. "no two products may share a
    name") still belong to Product/Request in domain/ and surface as a
    normal FAILURE result instead — see controller.py.

    JSON keys are camelCase (maxWeightKg, priceUsd, ...), matching the
    convention adapters/json_data_loader.py already established for this
    project's JSON I/O; Python field names stay snake_case via `alias`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProductSchema(BaseModel):
    """One candidate product in a solve request, mirroring domain.product.Product."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1)
    price_usd: float = Field(gt=0, alias="priceUsd")
    weight_kg: float = Field(gt=0, alias="weightKg")
    calories: int = Field(gt=0)


class SolveRequestSchema(BaseModel):
    """The body of POST /solve, mirroring domain.request.Request."""

    model_config = ConfigDict(populate_by_name=True)

    max_weight_kg: float = Field(gt=0, alias="maxWeightKg")
    max_budget_usd: float = Field(gt=0, alias="maxBudgetUsd")
    products: list[ProductSchema] = Field(min_length=1)


class RecommendationItemSchema(BaseModel):
    """One selected product and its quantity, within a SolveResponseSchema."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    quantity: int
    price_usd: float = Field(alias="priceUsd")
    weight_kg: float = Field(alias="weightKg")
    calories: int


class RecommendationSchema(BaseModel):
    """The recommended selection and its totals, within a SolveResponseSchema."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[RecommendationItemSchema]
    total_cost_usd: float = Field(alias="totalCostUsd")
    total_weight_kg: float = Field(alias="totalWeightKg")
    total_calories: int = Field(alias="totalCalories")


class SolveResponseSchema(BaseModel):
    """The body of POST /solve's response, mirroring use_cases.OptimizationResponse."""

    model_config = ConfigDict(populate_by_name=True)

    status: str
    message: str | None = None
    recommendation: RecommendationSchema | None = None
