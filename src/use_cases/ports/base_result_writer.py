"""
ROLE: Abstract Base Class — contract for persisting an optimization result to disk.

WHY THIS EXISTS:
    The CLI needs to save every run's input and solution somewhere, but the
    rest of the system should not need to know whether that "somewhere" is a
    folder of CSV files, a database, or a cloud bucket. This base class
    declares the one method any result-persistence strategy must provide, so
    a future format (e.g. Excel) is a new class, not a rewrite of the caller.

WHERE IMPLEMENTATIONS LIVE:
    Concrete writers live in src/adapters/, e.g. csv_result_writer.py and
    json_result_writer.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from use_cases.optimization_response import OptimizationResponse

# Every run folder is named after the moment its response was created, down
# to the second. Defined on the port (not inside one concrete writer) so
# every BaseResultWriter implementation shares the same folder-naming
# convention, and callers that must predict a run's folder before writing
# even starts (e.g. cli.py, which hands the solver an output_dir up front)
# have one shared format to import instead of picking an arbitrary writer's.
TIMESTAMP_FORMAT = "%Y_%m_%d_%H_%M_%S"


class BaseResultWriter(ABC):
    """
    This is an abstract base class (ABC) - a contract pattern, the mirror
    image of BaseDataLoader on the output side: it declares what a result
    writer must do without dictating how or in what file format. Any class
    that inherits from BaseResultWriter must provide a ``write()`` method, so
    callers can persist a run's results without caring whether they end up
    as CSV, JSON, or something else entirely.
    """

    @abstractmethod
    def write(self, request_id: str, response: OptimizationResponse, input_path: Path) -> Path:
        """Persist the response, alongside a copy of its input, to disk.

        Args:
            request_id: Identifier of the request that was solved.
            response: The result of solving that request.
            input_path: Path to the raw input file that was solved, so it can
                be copied alongside the result for reproducibility.

        Returns:
            The folder this run's files were written into.
        """
