"""
ROLE: Implementation — of BaseResultWriter, saving each run as JSON files.

WHY THIS EXISTS:
    Mirrors CsvResultWriter's responsibilities (copy input, write status,
    write solution) using JSON instead of CSV/plain text, so a run's output
    format is a choice made once at the composition root (startup.py)
    rather than a hardcoded assumption baked into the rest of the system.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from domain.recommendation import Recommendation
from use_cases.optimization_response import OptimizationResponse
from use_cases.ports.base_result_writer import TIMESTAMP_FORMAT, BaseResultWriter


class JsonResultWriter(BaseResultWriter):
    """Writes each run's input and solution under output_folder_path/<request_id>/<timestamp>/."""

    def __init__(self, output_folder_path: str) -> None:
        # Store the root folder so tests can point to a temp directory,
        # and production code can point to "output/".
        self._output_folder_path = Path(output_folder_path)

    def write(self, request_id: str, response: OptimizationResponse, input_path: Path) -> Path:
        run_folder = self._output_folder_path / request_id / response.timestamp.strftime(TIMESTAMP_FORMAT)
        run_folder.mkdir(parents=True, exist_ok=True)

        shutil.copy(input_path, run_folder / "input.json")

        status = {"status": response.status, "message": response.message}
        (run_folder / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

        if response.recommendation is not None:
            self._write_solution_json(run_folder / "solution.json", response.recommendation)

        return run_folder

    def _write_solution_json(self, path: Path, recommendation: Recommendation) -> None:
        # One entry per product in the catalog, not just the purchased ones,
        # so a reader can see at a glance which products were considered but
        # rejected by the optimizer, not only which ones were bought.
        products = []
        total_quantity = 0
        for product in recommendation.request.products:
            quantity = recommendation.quantities.get(product, 0)
            total_quantity += quantity
            products.append(
                {
                    "name": product.name,
                    "price_usd": product.price_usd,
                    "weight_kg": product.weight_kg,
                    "calories": product.calories,
                    "quantity": quantity,
                    "line_cost_usd": product.price_usd * quantity,
                    "line_weight_kg": product.weight_kg * quantity,
                    "line_calories": product.calories * quantity,
                }
            )
        solution = {
            "products": products,
            "total_quantity": total_quantity,
            "total_cost_usd": recommendation.total_cost_usd,
            "total_weight_kg": recommendation.total_weight_kg,
            "total_calories": recommendation.total_calories,
        }
        path.write_text(json.dumps(solution, indent=2), encoding="utf-8")
