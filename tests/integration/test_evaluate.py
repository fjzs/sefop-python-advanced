"""End-to-end integration test for the `evaluate` CLI subcommand.

Drives the real CLI (cli.main()) against tests/resources/feasible_unique_optimum/,
pairing its existing data.json with a small candidate_solution.json fixture.
"""

from pathlib import Path

import pytest

from frameworks_and_drivers import cli

_RESOURCES_DIR = Path(__file__).parent.parent / "resources"


@pytest.mark.integration
def test__cli_main__evaluate__given_feasible_candidate__prints_totals_and_exits_zero(monkeypatch, capsys):
    # ARRANGE — 1 protein_bar ($4, 2kg) + 2 chips ($6, 2kg) = $10/4kg,
    # within the request's $10 budget and 5kg limit.
    solution_path = _RESOURCES_DIR / "feasible_unique_optimum" / "candidate_solution.json"
    monkeypatch.setattr(
        "sys.argv",
        ["cli", "evaluate", "feasible_unique_optimum", str(solution_path), "--data-folder", str(_RESOURCES_DIR)],
    )

    # ACT
    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    # ASSERT
    assert exc_info.value.code == 0
    printed = capsys.readouterr().out
    assert "Feasible" in printed
    assert "calories=500" in printed


@pytest.mark.integration
def test__cli_main__evaluate__given_unknown_request_id__exits_nonzero(monkeypatch, capsys, tmp_path):
    # ARRANGE
    solution_path = tmp_path / "solution.json"
    solution_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["cli", "evaluate", "does-not-exist", str(solution_path), "--data-folder", str(_RESOURCES_DIR)],
    )

    # ACT
    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    # ASSERT
    assert exc_info.value.code == 1
    assert "Infeasible" in capsys.readouterr().out
