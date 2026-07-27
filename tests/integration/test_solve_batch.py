"""End-to-end integration test for the `solve-batch` CLI subcommand.

Drives the real CLI (cli.main()) with `solve-batch` pointed at
tests/resources/, which already holds one subfolder per "situation" used by
test_situations.py — a ready-made batch of several request IDs, both
feasible and infeasible, without needing a separate fixture folder.
"""

from pathlib import Path

import pytest

import cli

_RESOURCES_DIR = Path(__file__).parent.parent / "resources"


@pytest.mark.integration
def test__cli_main__solve_batch__solves_every_situation_and_exits_nonzero_when_one_is_infeasible(
    integration_output_root, monkeypatch, capsys
):
    # ARRANGE — tests/resources/infeasible/ has no feasible solution, so the
    # batch as a whole must report failure even though the rest succeed.
    batch_output_root = integration_output_root / "batch"
    monkeypatch.setattr(
        "sys.argv",
        ["cli", "solve-batch", str(_RESOURCES_DIR), "--output-folder", str(batch_output_root)],
    )

    # ACT
    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    # ASSERT
    assert exc_info.value.code == 1
    printed = capsys.readouterr().out
    assert "Results for request feasible_unique_optimum written to" in printed
    assert "Results for request infeasible written to" in printed
    assert (batch_output_root / "feasible_unique_optimum").exists()
    assert (batch_output_root / "infeasible").exists()
