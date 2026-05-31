"""
Guest collector – discovers and assesses guest hosts via Ansible inventories.

Authentication and transport are Ansible's responsibility.
This collector never reads credentials.
"""

from __future__ import annotations

import shutil

from collector.base import BaseCollector


class GuestCollector(BaseCollector):
    name = "guests"
    description = "Guest host facts collected via ansible-inventory and Ansible fact modules"

    def __init__(self, inventory_path: str | None = None) -> None:
        self._inventory_path = inventory_path

    def is_available(self) -> bool:
        return shutil.which("ansible-inventory") is not None

    def collect(self) -> dict:
        if not self._inventory_path:
            return {"error": "No inventory_path configured for GuestCollector"}

        from engine.modules.guest_inventory import collect_all_guests

        try:
            guests = collect_all_guests(self._inventory_path)
            return {"guests": guests, "inventory_path": self._inventory_path}
        except Exception as exc:
            return {"error": str(exc), "inventory_path": self._inventory_path}
