"""Exceptions raised by the TapHome SDK."""

from __future__ import annotations


class TapHomeError(Exception):
    """Base exception for all TapHome SDK errors."""


class TapHomeAuthError(TapHomeError):
    """The TapHome API rejected the configured token."""

    def __init__(self, status: int) -> None:
        """Store the HTTP status that triggered the error."""
        self.status = status
        super().__init__(f"TapHome API rejected the token (HTTP {status})")


class TapHomeConnectionError(TapHomeError):
    """The TapHome API could not be reached or returned an invalid response."""
