"""Shared fixtures for the CLI integration test suite.

WHY THIS EXISTS:
    Every integration test drives the real CLI end-to-end and produces real
    output files (input.json, status.txt, solution.csv, model.lp) that are
    worth keeping around after a run -- to inspect a failure, or to
    sanity-check a model.lp by eye. Pytest's tmp_path is deleted right after
    each test, destroying that evidence, so this suite writes to a
    persistent folder under output/ instead.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from use_cases.ports.base_result_writer import TIMESTAMP_FORMAT

# Anchored to this file rather than the current working directory so the
# suite always writes to the same place regardless of where `pytest` is
# invoked from (same convention as _RESOURCES_DIR in test_situations.py).
_REPO_ROOT = Path(__file__).parents[2]


@pytest.fixture(scope="session")
def integration_output_root() -> Path:
    """Output root every situation in this pytest session writes its CLI run under.

    One timestamp is captured per pytest session, not per test, so every
    situation from a single test run lands side by side under
    output/integration_tests/<session_timestamp>/ instead of each getting
    its own throwaway folder -- making it possible to inspect or diff an
    entire run's output as one unit. Reuses TIMESTAMP_FORMAT from the
    BaseResultWriter port rather than inventing a second format, since
    CsvResultWriter nests its own per-response timestamp folder one level
    below whatever this fixture returns.

    Returns:
        output/integration_tests/<timestamp>, relative to the repo root.
        Not created here -- CsvResultWriter.write() creates it (and the
        situation/response-timestamp folders nested under it) on first use.
    """
    timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    return _REPO_ROOT / "output" / "integration_tests" / timestamp
