"""
ROLE: Implementation — of BaseSolutionLoader, reading a candidate solution from JSON.

WHY THIS EXISTS:
    This module is the only place in the codebase that knows the on-disk
    format of a candidate solution file. EvaluateSolutionForRequest only
    talks to the abstract BaseSolutionLoader; this is one concrete
    implementation of it.
"""

from __future__ import annotations

import json
from pathlib import Path

from use_cases.ports.base_solution_loader import BaseSolutionLoader


class JsonSolutionLoader(BaseSolutionLoader):
    """Reads a candidate solution from a JSON file mapping product name to quantity.

    Expected format: ``{"product_name": quantity, ...}``, where every
    quantity is a positive integer. Mapping product names to actual Product
    instances on a specific Request is the caller's job, not this loader's.
    """

    def load(self, path: Path) -> dict[str, int] | None:
        """Load candidate product quantities from a JSON file.

        Args:
            path: Path to the JSON file describing the candidate solution.

        Returns:
            Mapping from product name to candidate quantity, or None if the
            file does not exist.

        Raises:
            ValueError: If the file exists but is not valid JSON, is not a
                flat object, or contains a non-positive quantity.
        """
        if not path.exists():
            return None  # "not found" — matches BaseDataLoader's contract

        raw = path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Solution file '{path}' is not valid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"Solution file '{path}' must contain a JSON object mapping product name to quantity")

        quantities: dict[str, int] = {}
        for name, quantity in data.items():
            if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
                raise ValueError(f"Quantity for product '{name}' must be a positive integer, got {quantity!r}")
            quantities[name] = quantity
        return quantities
