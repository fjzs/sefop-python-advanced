"""
ROLE: Abstract Base Class — contract for discovering which request IDs exist in a batch.

WHY THIS EXISTS:
    SolveMultipleRequests needs to know which request IDs to solve before it
    can loop over them, but it should not need to know whether those IDs come
    from scanning a folder, querying a database, or reading a manifest file.
    This base class declares the one method any discovery strategy must
    provide.

WHERE IMPLEMENTATIONS LIVE:
    Concrete discovery strategies live in src/adapters/, e.g.
    directory_request_discovery.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseRequestDiscovery(ABC):
    """
    This is an abstract base class (ABC) - a contract pattern: it declares
    the one method every discovery strategy must provide, without dictating
    how request IDs are found. Any class that inherits from
    BaseRequestDiscovery must provide a ``list_ids()`` method, so
    SolveMultipleRequests can enumerate a batch of requests without caring
    where they come from.
    """

    @abstractmethod
    def list_ids(self) -> list[str]:
        """Return the identifiers of every request available to solve.

        Returns:
            A list of request IDs, in whatever order this strategy considers
            deterministic (e.g. sorted alphabetically for a directory scan).
        """
