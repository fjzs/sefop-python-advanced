"""
ROLE: Implementation — of BaseRequestDiscovery, scanning a folder for request subfolders.

WHY THIS EXISTS:
    This module is the only place (besides JsonDataLoader) that knows request
    data lives at "{folder}/{request_id}/data.json". SolveMultipleRequests
    only talks to the abstract BaseRequestDiscovery; this is one concrete
    implementation of it.
"""

from __future__ import annotations

from pathlib import Path

from use_cases.ports.base_request_discovery import BaseRequestDiscovery


class DirectoryRequestDiscovery(BaseRequestDiscovery):
    """Discovers request IDs by scanning the immediate subfolders of a folder.

    A subfolder counts as a request if it contains a data.json file — the
    same convention JsonDataLoader uses to load one. The subfolder's name is
    used as the request ID.
    """

    def __init__(self, folder_path: str) -> None:
        self._folder_path = Path(folder_path)

    def list_ids(self) -> list[str]:
        """Return the sorted names of every immediate subfolder containing data.json.

        Returns:
            Sorted list of request IDs, so batch runs are deterministic
            regardless of the operating system's directory-listing order.
        """
        if not self._folder_path.exists():
            return []
        ids = [child.name for child in self._folder_path.iterdir() if child.is_dir() and (child / "data.json").exists()]
        return sorted(ids)
