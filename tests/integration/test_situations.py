"""End-to-end integration tests for the knapsack optimizer.

Each test drives the real CLI (cli.main()) against one pre-built "situation"
folder under tests/resources/. Together the situations cover the range of
behaviors the optimization pipeline needs to get right: a clean feasible optimum,
total infeasibility, ties between optimal solutions, the MIP/heuristic strategy switch,
preprocessing's filtering of individually-infeasible products, quantities above 1,
and both constraints binding at once.
"""

import csv
import math
from pathlib import Path

import pytest

import cli

_RESOURCES_DIR = Path(__file__).parent.parent / "resources"


def _run_cli(
    situation: str,
    integration_output_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> tuple[Path, int]:
    """Run cli.main() against a named situation folder.

    Points --data-folder straight at tests/resources (no chdir needed) and
    --output-folder at integration_output_root, the folder every situation
    in this pytest session shares (see the integration_output_root fixture
    in conftest.py), so situations never touch the real data/ or output/
    folders used by production runs.

    Args:
        situation: Name of the subfolder under tests/resources/ to solve;
            doubles as the request_id passed to the CLI.
        integration_output_root: Session-scoped output root this run's
            situations all write their CLI output under.
        monkeypatch: Used to substitute sys.argv for the duration of the call.
        capsys: Used to capture the "Results written to <path>" line the CLI prints.

    Returns:
        The run folder cli.main() reported writing to, and its exit code.
    """
    monkeypatch.setattr(
        "sys.argv",
        [
            "cli",
            "solve",
            situation,
            "--data-folder",
            str(_RESOURCES_DIR),
            "--output-folder",
            str(integration_output_root),
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    printed = capsys.readouterr().out.strip()
    run_folder = Path(printed.removeprefix("Results written to ").strip())
    return run_folder, exc_info.value.code


def _read_totals(run_folder: Path) -> dict[str, float]:
    """Parse the TOTAL row of solution.csv into its four numeric columns."""
    with (run_folder / "solution.csv").open(newline="", encoding="utf-8") as f:
        *_, total_row = csv.reader(f)
    return {
        "quantity": float(total_row[4]),
        "cost": float(total_row[5]),
        "weight": float(total_row[6]),
        "calories": float(total_row[7]),
    }


@pytest.mark.integration
def test__cli_main__given_feasible_unique_optimum__returns_expected_optimal_calories(
    integration_output_root, monkeypatch, capsys
):
    # ARRANGE / ACT — 1 protein_bar + 2 chips (500 cal, using the full budget)
    # beats every other combination that fits in budget=10/weight=5.
    run_folder, exit_code = _run_cli("feasible_unique_optimum", integration_output_root, monkeypatch, capsys)

    # ASSERT
    assert exit_code == 0
    assert "SUCCESS" in (run_folder / "status.txt").read_text(encoding="utf-8")
    assert math.isclose(_read_totals(run_folder)["calories"], 500)


@pytest.mark.integration
def test__cli_main__given_infeasible__exits_nonzero_and_writes_no_solution(
    integration_output_root, monkeypatch, capsys
):
    # ARRANGE / ACT — the only product costs more than the entire budget, so
    # preprocessing filters it out and no recommendation exists.
    run_folder, exit_code = _run_cli("infeasible", integration_output_root, monkeypatch, capsys)

    # ASSERT
    assert exit_code == 1
    assert "FAILURE" in (run_folder / "status.txt").read_text(encoding="utf-8")
    assert not (run_folder / "solution.csv").exists()


@pytest.mark.integration
def test__cli_main__given_multiple_optimal_solutions__returns_shared_optimal_calories(
    integration_output_root, monkeypatch, capsys
):
    # ARRANGE / ACT — cookie_a and cookie_b are interchangeable (same price,
    # weight, and calories), so either one alone is an optimal pick. Assert
    # only the shared optimal total, never which cookie the solver preferred.
    run_folder, exit_code = _run_cli("multiple_optimal_solutions", integration_output_root, monkeypatch, capsys)

    # ASSERT
    assert exit_code == 0
    assert math.isclose(_read_totals(run_folder)["calories"], 100)


@pytest.mark.integration
def test__cli_main__given_large_instance__triggers_heuristic_and_returns_feasible_solution(
    integration_output_root, monkeypatch, capsys
):
    # ARRANGE / ACT — 55 feasible products exceeds orchestrator.MAX_PRODUCTS_FOR_MIP
    # (50), routing this request to the greedy heuristic instead of exact MIP.
    # The heuristic isn't guaranteed optimal, so only feasibility is checked.
    run_folder, exit_code = _run_cli("large_instance_triggers_heuristic", integration_output_root, monkeypatch, capsys)

    # ASSERT
    assert exit_code == 0
    totals = _read_totals(run_folder)
    assert totals["cost"] <= 20
    assert totals["weight"] <= 3.0
    assert totals["calories"] > 0


@pytest.mark.integration
def test__cli_main__given_individually_infeasible_products__filters_them_and_solves_with_the_rest(
    integration_output_root, monkeypatch, capsys
):
    # ARRANGE / ACT — luxury_item (too expensive) and heavy_item (too heavy)
    # are filtered out by preprocessing on their own, before the solver ever
    # sees them; only affordable_snack remains to build the recommendation.
    run_folder, exit_code = _run_cli(
        "individually_infeasible_product_filtered", integration_output_root, monkeypatch, capsys
    )

    # ASSERT
    assert exit_code == 0
    assert math.isclose(_read_totals(run_folder)["calories"], 120)


@pytest.mark.integration
def test__cli_main__given_quantity_greater_than_one__selects_multiple_units_of_same_product(
    integration_output_root, monkeypatch, capsys
):
    # ARRANGE / ACT — a single cheap, light product means the optimum buys
    # 10 units of it, confirming the model isn't restricted to 0/1 per product.
    run_folder, exit_code = _run_cli("quantity_greater_than_one", integration_output_root, monkeypatch, capsys)

    # ASSERT
    assert exit_code == 0
    totals = _read_totals(run_folder)
    assert math.isclose(totals["quantity"], 10)
    assert math.isclose(totals["calories"], 500)


@pytest.mark.integration
def test__cli_main__given_both_constraints_binding__saturates_budget_and_weight_together(
    integration_output_root, monkeypatch, capsys
):
    # ARRANGE / ACT — 4 x_item + 1 y_item exactly exhausts both the budget
    # and the weight limit at the same time, unlike the other feasible cases
    # where only one constraint binds.
    run_folder, exit_code = _run_cli("both_constraints_binding", integration_output_root, monkeypatch, capsys)

    # ASSERT
    assert exit_code == 0
    totals = _read_totals(run_folder)
    assert math.isclose(totals["cost"], 9)
    assert math.isclose(totals["weight"], 6)
    assert math.isclose(totals["calories"], 145)
