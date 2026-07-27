"""Configuration and composition root for the application.

This module has two jobs, kept together because they're two sides of the
same coin:

1. Hold every configurable value (the `Settings` dataclass) in one place,
   rather than scattered as literal strings across the codebase. A data
   scientist forking this repository to point at their own data or output
   folder only needs to edit `Settings` here.
2. Assemble the object graph each delivery mechanism needs (the `build_*`
   factory functions — one family for the CLI, one for the web app). This is
   the only module in the codebase allowed to import concrete adapters and
   construct concrete use cases directly. frameworks_and_drivers/cli.py and
   frameworks_and_drivers/web/ call these factory functions instead of
   constructing anything themselves, so every other module can depend on
   abstract ports (use_cases/ports/) without knowing which concrete adapter
   ultimately gets wired in.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from adapters.csv_result_writer import CsvResultWriter
from adapters.directory_request_discovery import DirectoryRequestDiscovery
from adapters.json_data_loader import JsonDataLoader
from adapters.json_result_writer import JsonResultWriter
from adapters.json_solution_loader import JsonSolutionLoader
from adapters.web.in_memory_data_loader import InMemoryDataLoader
from use_cases.ports.base_data_loader import BaseDataLoader
from use_cases.ports.base_request_discovery import BaseRequestDiscovery
from use_cases.ports.base_result_writer import BaseResultWriter
from use_cases.solving.optimization.enumeration.enumeration_solution_provider import EnumerationSolutionProvider
from use_cases.solving.optimization.heuristic.heuristic_solution_provider import HeuristicSolutionProvider
from use_cases.solving.optimization.mip_google.mip_google_scip_solution_provider import (
    MipGoogleScipSolutionProvider,
)
from use_cases.solving.optimization.mip_highs.mip_highs_solution_provider import MipHighsSolutionProvider
from use_cases.solving.optimization.solution_provider import SolutionProvider
from use_cases.solving.orchestrator import Orchestrator
from use_cases.solving.postprocessing.postprocessing import PostProcess
from use_cases.solving.preprocessing.preprocessing import PreProcess
from use_cases.use_case_evaluate_solution_for_request import EvaluateSolutionForRequest
from use_cases.use_case_solve_multiple_requests import SolveMultipleRequests
from use_cases.use_case_solve_single_request import SolveSingleRequest


@dataclass
class Settings:
    """Holds all configurable values for the application.

    Attributes:
        folder_path: Root directory where request subfolders live
            (data/1/data.json, data/2/data.json, …).
        solver_name: Solver technology passed to the MIP SolutionProvider.
        output_folder_path: Root directory each run's input and solution
            files are written under (output/1/<timestamp>/, …).
    """

    folder_path: str = "data"
    solver_name: str = "google_scip"
    output_folder_path: str = "output"


@dataclass
class WebSettings:
    """Holds configurable values for the web delivery mechanism.

    A separate type from Settings, not a reuse of it: the web flow never
    reads a request from a file or writes a result to one, so it has no use
    for folder_path/output_folder_path. Giving it its own dataclass means it
    only carries fields it actually uses.

    Attributes:
        solver_name: Solver technology passed to the MIP SolutionProvider.
            Read from the SOLVER_NAME environment variable (falling back to
            "google_scip") so the Docker image can select a solver without a
            code change.
    """

    solver_name: str = field(default_factory=lambda: os.environ.get("SOLVER_NAME", "google_scip"))


def build_mip_solution_provider(settings: Settings) -> SolutionProvider:
    """Resolve settings.solver_name to a concrete MIP SolutionProvider.

    This is the one place in the codebase where a solver name string is
    mapped to a class. Adding another MIP technology (as MipGoogleScipSolutionProvider
    was added alongside MipHighsSolutionProvider) means adding one more branch here and
    a new SolutionProvider implementation — nothing else in the codebase needs to
    change.

    Args:
        settings: Application settings; only solver_name is used.

    Returns:
        The provider instance matching settings.solver_name.

    Raises:
        ValueError: If settings.solver_name does not match a known solver.
    """
    if settings.solver_name == "highs":
        return MipHighsSolutionProvider()
    if settings.solver_name == "google_scip":
        return MipGoogleScipSolutionProvider()
    raise ValueError(f"Unknown solver '{settings.solver_name}'. Available: ['highs', 'google_scip']")


def build_orchestrator(settings: Settings) -> Orchestrator:
    """Assemble an Orchestrator with all of its solving-pipeline collaborators.

    Args:
        settings: Application settings; forwarded to
            build_mip_solution_provider() to pick the MIP solver technology.

    Returns:
        A fully wired Orchestrator, ready to solve a Request.
    """
    return Orchestrator(
        preprocessing=PreProcess(),
        postprocessing=PostProcess(),
        mip_solution_provider=build_mip_solution_provider(settings),
        heuristic_solution_provider=HeuristicSolutionProvider(),
        enumeration_solution_provider=EnumerationSolutionProvider(),
    )


def build_solve_single_request(settings: Settings, folder_path: str | None = None) -> SolveSingleRequest:
    """Assemble a SolveSingleRequest use case.

    Args:
        settings: Application settings; solver_name is forwarded to
            build_orchestrator().
        folder_path: Folder to load request data from. Defaults to
            settings.folder_path when omitted, so a caller solving a batch
            from a different folder (SolveMultipleRequests) can point this
            use case elsewhere without touching Settings.

    Returns:
        A fully wired SolveSingleRequest, ready to solve one request ID.
    """
    return SolveSingleRequest(
        request_loader=JsonDataLoader(folder_path=folder_path or settings.folder_path),
        orchestrator=build_orchestrator(settings),
    )


def build_request_discovery(folder_path: str) -> BaseRequestDiscovery:
    """Assemble a BaseRequestDiscovery scanning folder_path for requests.

    Args:
        folder_path: Root folder to scan for request subfolders.

    Returns:
        A DirectoryRequestDiscovery over folder_path.
    """
    return DirectoryRequestDiscovery(folder_path=folder_path)


def build_solve_multiple_requests(settings: Settings, folder_path: str) -> SolveMultipleRequests:
    """Assemble a SolveMultipleRequests use case scanning folder_path for requests.

    Args:
        settings: Application settings; solver_name is forwarded to
            build_orchestrator().
        folder_path: Root folder to scan for request subfolders, and the
            same folder each discovered request is loaded from.

    Returns:
        A fully wired SolveMultipleRequests, ready to solve every request
        folder_path contains.
    """
    return SolveMultipleRequests(
        request_discovery=build_request_discovery(folder_path),
        solve_single_request=build_solve_single_request(settings, folder_path=folder_path),
    )


def build_evaluate_solution_for_request(
    settings: Settings, folder_path: str | None = None
) -> EvaluateSolutionForRequest:
    """Assemble an EvaluateSolutionForRequest use case.

    Args:
        settings: Application settings.
        folder_path: Folder to load request data from. Defaults to
            settings.folder_path when omitted.

    Returns:
        A fully wired EvaluateSolutionForRequest, ready to evaluate a
        candidate solution against one request ID.
    """
    return EvaluateSolutionForRequest(
        request_loader=JsonDataLoader(folder_path=folder_path or settings.folder_path),
        solution_loader=JsonSolutionLoader(),
    )


def build_result_writer(settings: Settings, format_: str = "csv") -> BaseResultWriter:
    """Select the concrete BaseResultWriter matching the requested output format.

    Args:
        settings: Application settings; output_folder_path is where the
            writer persists each run.
        format_: Either "csv" or "json"; selects which concrete writer to build.

    Returns:
        The writer instance matching format_.

    Raises:
        ValueError: If format_ is neither "csv" nor "json".
    """
    if format_ == "csv":
        return CsvResultWriter(output_folder_path=settings.output_folder_path)
    if format_ == "json":
        return JsonResultWriter(output_folder_path=settings.output_folder_path)
    raise ValueError(f"Unknown format '{format_}'. Available: ['csv', 'json']")


def build_web_solve_single_request(settings: WebSettings, request_loader: BaseDataLoader) -> SolveSingleRequest:
    """Assemble a SolveSingleRequest use case for the web delivery mechanism.

    Unlike build_solve_single_request (CLI), the web flow never reads a
    request from disk: request_loader is the caller-supplied InMemoryDataLoader
    that already holds the Request built from the HTTP request body, keyed by
    a synthetic id the caller also generated. This factory only needs
    solver_name from WebSettings, which it forwards to build_orchestrator via
    a throwaway Settings instance — build_orchestrator only ever reads
    solver_name off it, so the unused folder-path fields never surface.

    Args:
        settings: Web application settings; solver_name is forwarded to
            build_orchestrator().
        request_loader: The InMemoryDataLoader instance the caller already
            stored the incoming Request in.

    Returns:
        A fully wired SolveSingleRequest, ready to solve the request_id
        request_loader was given.
    """
    return SolveSingleRequest(
        request_loader=request_loader,
        orchestrator=build_orchestrator(Settings(solver_name=settings.solver_name)),
    )


def build_in_memory_data_loader() -> InMemoryDataLoader:
    """Assemble a fresh InMemoryDataLoader for one web request.

    A new instance per HTTP request (never shared or reused across requests)
    keeps one submitted problem from ever being visible to another — see
    adapters/web/in_memory_data_loader.py for why that matters.

    Returns:
        An empty InMemoryDataLoader, ready to have one Request stored in it.
    """
    return InMemoryDataLoader()
