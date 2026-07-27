"""Implementation of BaseDataLoader that holds a Request in memory instead of reading a file.

WHY THIS EXISTS:
    SolveSingleRequest.solve(request_id, ...) always loads its Request through
    a BaseDataLoader. The CLI's JsonDataLoader satisfies that by reading a
    file; the web app has no file to read — the HTTP request body already
    *is* the Request. This adapter closes that gap without changing
    SolveSingleRequest at all: the web controller stores the just-built
    Request here under a synthetic id, then calls solve() with that id like
    any other caller would.
"""

from __future__ import annotations

import uuid

from domain.request import Request
from use_cases.ports.base_data_loader import BaseDataLoader


class InMemoryDataLoader(BaseDataLoader):
    """Holds at most the Requests stored in it during this instance's lifetime.

    One instance is built fresh per HTTP request (see
    startup.build_in_memory_data_loader) and discarded once that request
    finishes, so nothing about one person's problem is ever visible to
    another's — there is no shared, long-lived store to leak across requests.
    """

    def __init__(self) -> None:
        self._requests: dict[str, Request] = {}

    def store(self, request: Request) -> str:
        """Store a Request and return the synthetic id it can be loaded back by.

        Args:
            request: The Request to make available to load().

        Returns:
            A freshly generated id, unique to this call.
        """
        request_id = str(uuid.uuid4())
        self._requests[request_id] = request
        return request_id

    def load(self, request_id: str) -> Request | None:
        """Return the Request previously passed to store() under request_id.

        Returns None for any id this instance was never given — matches the
        BaseDataLoader "not found" contract the CLI's JsonDataLoader also
        follows, so SolveSingleRequest's not-found handling works unchanged.
        """
        return self._requests.get(request_id)
