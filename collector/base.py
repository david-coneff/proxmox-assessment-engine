"""Base collector interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseCollector(ABC):
    """
    All collectors must implement this interface.

    collect() returns a raw dict of facts.  The dict is not normalized;
    the engine parser layer handles normalization.
    """

    #: Short lowercase identifier, must be unique across all collectors.
    name: str = ""

    #: Human-readable description of what this collector gathers.
    description: str = ""

    @abstractmethod
    def collect(self) -> dict:
        """Collect facts and return them as a raw dict."""

    def is_available(self) -> bool:
        """
        Return True if the collector can run on this system.

        Override to check for required binaries or privileges.
        Default: always available.
        """
        return True
