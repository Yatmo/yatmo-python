"""HTTP transport: a tiny protocol so any HTTP library (requests, httpx) can replace the standard-library one."""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Mapping, Protocol, Tuple


class Transport(Protocol):
    def get(self, url: str, headers: Mapping[str, str], timeout_seconds: float) -> Tuple[int, bytes]:
        """GET ``url`` with ``headers``; returns ``(status, body)``. Raises on network failure."""


class UrllibTransport:
    """The default transport, standard library only."""

    def get(self, url: str, headers: Mapping[str, str], timeout_seconds: float) -> Tuple[int, bytes]:
        request = urllib.request.Request(url, headers=dict(headers), method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 (https URL built by the client)
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()
