"""
ROLE: Abstract Base Class — contract that every data-loading strategy must follow.

WHY THIS EXISTS:
    The optimization use cases load input data through this interface, so the
    source of data (Excel file, database, REST API, etc.) can change without
    modifying the optimization logic itself.

WHERE IMPLEMENTATIONS LIVE:
    Concrete loaders live in src/adapters/, e.g. json_data_loader.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.request import Request


class BaseDataLoader(ABC):
    """
    An abstract base class (ABC) is like a contract: it declares methods
    that every data loader **must** implement, without dictating *how* the
    data is fetched. Any class that inherits from ``BaseDataLoader`` must
    provide a ``load()`` method, so the rest of the system can load data
    without caring whether it comes from a spreadsheet, a database, or an
    API.

    Implementations load request data from files, databases, APIs, etc., and
    live in ``src/adapters/``, e.g. ``json_data_loader.py``.
    """

    @abstractmethod
    def load(self, request_id: str) -> Request | None:
        """Load the data from the request and returns it.

        Args:
            request_id: Unique identifier of the request to load.

        Returns:
            The loaded Request, or None if not found.
        """
