"""
ROLE: Implementation — of BaseResultWriter, saving each run as plain CSV/text files.

WHY THIS EXISTS:
    This module is the only place in the codebase that knows about CSV files
    or the on-disk run folder layout. The rest of the system talks to the
    abstract BaseResultWriter; this is one concrete implementation of it,
    chosen because CSV and plain text need no dependency beyond Python's
    standard library.
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

from domain.recommendation import Recommendation
from use_cases.optimization_response import OptimizationResponse
from use_cases.ports.base_result_writer import TIMESTAMP_FORMAT, BaseResultWriter

_CSV_HEADER = [
    "name",
    "price_usd",
    "weight_kg",
    "calories",
    "quantity",
    "line_cost_usd",
    "line_weight_kg",
    "line_calories",
]


class CsvResultWriter(BaseResultWriter):
    """Writes each run's input and solution under output_folder_path/<request_id>/<timestamp>/."""

    def __init__(self, output_folder_path: str) -> None:
        # Store the root folder so tests can point to a temp directory,
        # and production code can point to "output/".
        self._output_folder_path = Path(output_folder_path)

    def write(self, request_id: str, response: OptimizationResponse, input_path: Path) -> Path:
        run_folder = self._output_folder_path / request_id / response.timestamp.strftime(TIMESTAMP_FORMAT)
        run_folder.mkdir(parents=True, exist_ok=True)

        shutil.copy(input_path, run_folder / "input.json")

        # message is None on success, so fall back to an empty string rather
        # than writing the literal text "None" into the file.
        (run_folder / "status.txt").write_text(f"{response.status}\n{response.message or ''}\n", encoding="utf-8")

        if response.recommendation is not None:
            self._write_solution_csv(run_folder / "solution.csv", response.recommendation)

        return run_folder

    def _write_solution_csv(self, path: Path, recommendation: Recommendation) -> None:
        # One row per product in the catalog, not just the purchased ones, so a
        # reader can see at a glance which products were considered but
        # rejected by the optimizer, not only which ones were bought.
        total_quantity = 0
        total_cost = 0.0
        total_weight = 0.0
        total_calories = 0
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(_CSV_HEADER)
            for product in recommendation.request.products:
                quantity = recommendation.quantities.get(product, 0)
                line_cost = product.price_usd * quantity
                line_weight = product.weight_kg * quantity
                line_calories = product.calories * quantity
                writer.writerow(
                    [
                        product.name,
                        product.price_usd,
                        product.weight_kg,
                        product.calories,
                        quantity,
                        line_cost,
                        line_weight,
                        line_calories,
                    ]
                )
                total_quantity += quantity
                total_cost += line_cost
                total_weight += line_weight
                total_calories += line_calories
            writer.writerow(["TOTAL", "", "", "", total_quantity, total_cost, total_weight, total_calories])
