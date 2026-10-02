"""Errors of the Yatmo client: one class per HTTP status family, all subclasses of YatmoError."""

from __future__ import annotations


class YatmoError(RuntimeError):
    """An error answered by the Yatmo API (``status`` holds the HTTP status, 0 when the API was unreachable)."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status

    @staticmethod
    def from_status(status: int, message: str) -> "YatmoError":
        if status == 400:
            return BadRequestError(status, message)
        if status == 401:
            return AuthenticationError(status, message)
        if status == 403:
            return ForbiddenError(status, message)
        if status == 429:
            return QuotaError(status, message)
        return YatmoError(status, message)


class BadRequestError(YatmoError):
    """400: a parameter is wrong, or the position lies outside the country."""


class AuthenticationError(YatmoError):
    """401: the key is missing or unknown."""


class ForbiddenError(YatmoError):
    """403: the licence does not cover this country, endpoint or domain."""


class QuotaError(YatmoError):
    """429: the licence quota is exhausted."""


class TransportError(YatmoError):
    """The API could not be reached, or answered something unreadable."""
