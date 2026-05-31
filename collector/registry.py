"""Collector registry – discovers and holds all registered collectors."""

from __future__ import annotations

from collector.base import BaseCollector


class CollectorRegistry:
    """
    Holds the set of active collectors.

    Collectors are registered explicitly via register() or by importing
    the built-in collector modules (done in __init__ below).
    """

    def __init__(self) -> None:
        self._collectors: dict[str, BaseCollector] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        from collector.hardware import HardwareCollector
        from collector.storage import StorageCollector
        from collector.network import NetworkCollector
        from collector.proxmox import ProxmoxCollector

        for cls in (HardwareCollector, StorageCollector, NetworkCollector, ProxmoxCollector):
            instance = cls()
            self.register(instance)

    def register(self, collector: BaseCollector) -> None:
        if not collector.name:
            raise ValueError(f"{type(collector).__name__} must set a non-empty 'name'")
        self._collectors[collector.name] = collector

    @property
    def collectors(self) -> dict[str, BaseCollector]:
        return dict(self._collectors)

    def available(self) -> dict[str, BaseCollector]:
        """Return only collectors that report is_available() == True."""
        return {n: c for n, c in self._collectors.items() if c.is_available()}
