"""Command-line interface for the knapsack optimizer.

This is the delivery mechanism for the CLI. Its only job is to parse
arguments and dispatch to whatever startup.py assembles — it never
constructs a concrete adapter or use case itself; that composition-root
responsibility belongs entirely to startup.py.

Run with:
    python -m cli solve <request_id>
    python -m cli solve-batch <data_folder>
    python -m cli evaluate <request_id> <solution_path>
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import startup
from startup import Settings
from use_cases.ports.base_result_writer import TIMESTAMP_FORMAT


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with its three subcommands: solve, solve-batch, evaluate."""
    parser = argparse.ArgumentParser(description="Solve or evaluate knapsack optimization requests")
    subparsers = parser.add_subparsers(dest="command", required=True)

    solve_parser = subparsers.add_parser("solve", help="Solve a single request")
    solve_parser.add_argument(
        "request_id", help="ID of the request to solve (must match a subfolder under the data/ directory)."
    )
    solve_parser.add_argument(
        "--data-folder",
        default=None,
        help="Override the folder containing request subfolders (default: Settings().folder_path).",
    )
    solve_parser.add_argument(
        "--output-folder",
        default=None,
        help="Override the folder solutions are written to (default: Settings().output_folder_path).",
    )
    solve_parser.add_argument(
        "--format", choices=["csv", "json"], default="csv", help="Result file format (default: csv)."
    )

    batch_parser = subparsers.add_parser("solve-batch", help="Solve every request found in a folder")
    batch_parser.add_argument("data_folder", help="Folder containing one subfolder of request data per request ID.")
    batch_parser.add_argument(
        "--output-folder",
        default=None,
        help="Override the folder solutions are written to (default: Settings().output_folder_path).",
    )
    batch_parser.add_argument(
        "--format", choices=["csv", "json"], default="csv", help="Result file format (default: csv)."
    )

    evaluate_parser = subparsers.add_parser(
        "evaluate", help="Check whether a candidate solution is feasible for a request"
    )
    evaluate_parser.add_argument("request_id", help="ID of the request the candidate solution answers.")
    evaluate_parser.add_argument(
        "solution_path", help="Path to a JSON file mapping product name to candidate quantity."
    )
    evaluate_parser.add_argument(
        "--data-folder",
        default=None,
        help="Override the folder containing request subfolders (default: Settings().folder_path).",
    )

    return parser


def _solve(args: argparse.Namespace, settings: Settings) -> int:
    """Solve one request and write its result. Returns the process exit code."""
    data_folder = args.data_folder or settings.folder_path
    output_folder = args.output_folder or settings.output_folder_path
    settings = replace(settings, folder_path=data_folder, output_folder_path=output_folder)

    writer = startup.build_result_writer(settings, args.format)
    solve_single_request = startup.build_solve_single_request(settings)

    # Captured before solving starts (rather than left to default inside the
    # use case) so this exact instant can be handed to the solver as the
    # folder to dump model.lp into, and later reused by the writer -- both
    # must agree on the same run folder without recomputing timestamps
    # independently.
    timestamp = datetime.now()
    run_folder = Path(output_folder) / args.request_id / timestamp.strftime(TIMESTAMP_FORMAT)
    response = solve_single_request.solve(args.request_id, output_dir=run_folder, timestamp=timestamp)

    # The writer only knows how to copy a file, not where JsonDataLoader's
    # "{folder}/{request_id}/data.json" convention lives, so that path is
    # built here rather than inside the writer.
    input_path = Path(data_folder) / args.request_id / "data.json"
    run_folder = writer.write(args.request_id, response, input_path)
    print(f"Results written to {run_folder}")

    return 0 if response.recommendation is not None else 1


def _solve_batch(args: argparse.Namespace, settings: Settings) -> int:
    """Solve every request discovered under a folder and write each result.

    Returns the process exit code: 1 if any request had no recommendation.
    """
    output_folder = args.output_folder or settings.output_folder_path
    settings = replace(settings, folder_path=args.data_folder, output_folder_path=output_folder)

    writer = startup.build_result_writer(settings, args.format)
    solve_multiple_requests = startup.build_solve_multiple_requests(settings, args.data_folder)
    # A second, independent discovery scan: OptimizationResponse carries no
    # request_id field, so the ids returned here are what pairs each response
    # from solve_all() with the input file its writer needs to copy alongside
    # it. Harmless duplicate work -- discovery only reads folder names.
    request_discovery = startup.build_request_discovery(args.data_folder)

    timestamp = datetime.now()
    responses = solve_multiple_requests.solve_all(Path(output_folder), timestamp=timestamp)
    request_ids = request_discovery.list_ids()

    any_failed = False
    for request_id, response in zip(request_ids, responses):
        input_path = Path(args.data_folder) / request_id / "data.json"
        run_folder = writer.write(request_id, response, input_path)
        print(f"Results for request {request_id} written to {run_folder}")
        if response.recommendation is None:
            any_failed = True

    return 1 if any_failed else 0


def _evaluate(args: argparse.Namespace, settings: Settings) -> int:
    """Check feasibility of a candidate solution and print the outcome."""
    data_folder = args.data_folder or settings.folder_path
    settings = replace(settings, folder_path=data_folder)

    evaluate_solution_for_request = startup.build_evaluate_solution_for_request(settings)
    response = evaluate_solution_for_request.evaluate(args.request_id, Path(args.solution_path))

    if response.feasible:
        print(
            f"Feasible: calories={response.total_calories}, "
            f"cost_usd={response.total_cost_usd}, weight_kg={response.total_weight_kg}"
        )
        return 0

    print(f"Infeasible: {response.message}")
    return 1


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = _build_parser()
    args = parser.parse_args()
    settings = Settings()

    if args.command == "solve":
        exit_code = _solve(args, settings)
    elif args.command == "solve-batch":
        exit_code = _solve_batch(args, settings)
    elif args.command == "evaluate":
        exit_code = _evaluate(args, settings)
    else:
        raise AssertionError(f"Unhandled command: {args.command}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
