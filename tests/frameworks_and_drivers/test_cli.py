"""
ROLE: Unit test for cli.main()'s default folder resolution.

WHY THIS EXISTS:
    tests/integration/test_situations.py already exercises cli.main() end-to-end
    across many optimization scenarios, but every one of those runs passes
    explicit --data-folder/--output-folder flags. That leaves one behavior
    untested: what happens when a caller omits both flags and cli.main() must
    fall back to Settings().folder_path / Settings().output_folder_path, which
    are relative paths ("data"/"output") resolved against the current working
    directory. This file covers exactly that fallback path so it isn't lost
    once the flag-based behavior is fully covered elsewhere.
"""

import json
from pathlib import Path

import pytest

from frameworks_and_drivers import cli


def _write_request(data_root, request_id: str, payload: dict) -> None:
    folder = data_root / request_id
    folder.mkdir(parents=True)
    (folder / "data.json").write_text(json.dumps(payload), encoding="utf-8")


def test__cli_main__given_no_folder_flags__resolves_data_and_output_from_settings_relative_to_cwd(
    tmp_path, monkeypatch, capsys
):
    # ARRANGE — Settings().folder_path/output_folder_path are relative ("data"/"output"),
    # so chdir into a temp directory to prove main() finds them from the current
    # working directory rather than requiring --data-folder/--output-folder.
    monkeypatch.chdir(tmp_path)
    _write_request(
        tmp_path / "data",
        "1",
        {
            "requestId": "1",
            "maxWeightKg": 1.0,
            "maxBudgetUsd": 5.0,
            "products": [{"name": "banana", "priceUsd": 1.00, "weightKg": 0.50, "calories": 100}],
        },
    )
    monkeypatch.setattr("sys.argv", ["cli", "solve", "1"])

    # ACT
    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    # ASSERT
    assert exc_info.value.code == 0
    printed = capsys.readouterr().out.strip()
    assert printed.startswith("Results written to ")
    run_folder = Path(printed.removeprefix("Results written to ").strip())
    assert (run_folder / "solution.csv").exists()
    assert (run_folder / "input.json").exists()
