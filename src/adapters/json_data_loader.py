"""
ROLE: Implementation of BaseDataLoader that reads Request data from JSON.

WHY THIS EXISTS:
    This module is the only place in the codebase that knows about JSON files.
    The rest of the system talks to the abstract ``BaseDataLoader`` base class;
    this is one concrete implementation of it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from domain.product import Product
from domain.request import Request
from use_cases.ports.base_data_loader import BaseDataLoader


class JsonDataLoader(BaseDataLoader):
    """Reads JSON data files and returns domain objects.

    Design note — why camelCase in JSON, not snake_case:
      JSON files use camelCase (e.g. ``maxWeightKg``, ``priceUsd``) because
      that is the dominant convention for JSON APIs and external data sources.
      This class explicitly maps every camelCase key to its Python snake_case
      equivalent (e.g. ``maxWeightKg`` → ``max_weight_kg``).

      This mapping is intentional and belongs here. This class is the only place
      that knows about JSON — its job is to translate between the external
      world's conventions and the domain model's conventions. Domain objects
      (``Request``, ``Product``) never know about JSON — they only speak Python.
    """

    def __init__(self, folder_path: str) -> None:
        # Store the root folder so tests can point to a temp directory,
        # and production code can point to "data/".
        self._folder_path = Path(folder_path)

    def load(self, request_id: str) -> Request | None:
        """Load a Request from ``{folder_path}/{request_id}/data.json``.

        Returns None when the file does not exist — callers interpret None as
        "request not found". Raises ValueError when the file exists but its
        content is invalid, so data scientists catch bad data files early
        rather than silently getting a None they cannot debug.
        """
        path = self._folder_path / request_id / "data.json"
        if not path.exists():
            return None  # "not found" — matches BaseDataLoader contract

        raw = path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"data.json for request '{request_id}' is not valid JSON: {exc}") from exc

        return _parse_request(data, request_id)


def _parse_request(data: dict[str, Any], request_id: str) -> Request:
    """Map a camelCase JSON dict to a ``Request`` domain object.

    Raises ValueError on any missing or invalid field so the caller gets a
    clear error message instead of a confusing AttributeError or KeyError.
    """
    try:
        products = [_parse_product(p) for p in data["products"]]
        return Request(
            max_weight_kg=data["maxWeightKg"],
            max_budget_usd=data["maxBudgetUsd"],
            products=products,
        )
    except KeyError as exc:
        raise ValueError(f"data.json for request '{request_id}' is missing required field: {exc}") from exc


def _parse_product(data: dict[str, Any]) -> Product:
    """Map a camelCase JSON dict to a ``Product`` domain object."""
    try:
        return Product(
            name=data["name"],
            price_usd=data["priceUsd"],
            weight_kg=data["weightKg"],
            calories=data["calories"],
        )
    except KeyError as exc:
        raise ValueError(f"product entry is missing required field: {exc}") from exc
