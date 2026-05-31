"""Hardware collector – gathers CPU, memory, and system board facts."""

from __future__ import annotations

import shutil
import subprocess

from collector.base import BaseCollector


class HardwareCollector(BaseCollector):
    name = "hardware"
    description = "CPU, memory, and system board facts via dmidecode / /proc/cpuinfo"

    def is_available(self) -> bool:
        return shutil.which("dmidecode") is not None

    def collect(self) -> dict:
        return {
            "cpu": self._collect_cpu(),
            "memory": self._collect_memory(),
            "system": self._collect_dmi_type(1),
            "baseboard": self._collect_dmi_type(2),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run(self, cmd: list[str]) -> str:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"Command {cmd} failed: {result.stderr.strip()}")
        return result.stdout

    def _collect_cpu(self) -> dict:
        """Parse /proc/cpuinfo for CPU facts."""
        try:
            text = open("/proc/cpuinfo").read()
        except OSError:
            return {}

        processors: list[dict] = []
        current: dict = {}
        for line in text.splitlines():
            if line.strip() == "":
                if current:
                    processors.append(current)
                    current = {}
            elif ":" in line:
                key, _, val = line.partition(":")
                current[key.strip()] = val.strip()
        if current:
            processors.append(current)

        if not processors:
            return {}

        first = processors[0]
        physical_ids = {p.get("physical id") for p in processors if "physical id" in p}
        sockets = len(physical_ids) if physical_ids else 1

        core_ids = {
            (p.get("physical id"), p.get("core id"))
            for p in processors
            if "physical id" in p and "core id" in p
        }
        total_cores = len(core_ids) if core_ids else len(processors)
        total_threads = len(processors)

        flags = first.get("flags", "").split()

        return {
            "model": first.get("model name", ""),
            "vendor": first.get("vendor_id", ""),
            "sockets": sockets,
            "cores_per_socket": total_cores // max(sockets, 1),
            "threads_per_core": total_threads // max(total_cores, 1),
            "total_cores": total_cores,
            "total_threads": total_threads,
            "architecture": "x86_64",  # best effort; extend if needed
            "flags": flags,
        }

    def _collect_memory(self) -> dict:
        """Parse dmidecode type 17 for DIMM facts."""
        try:
            raw = self._run(["dmidecode", "-t", "17"])
        except (RuntimeError, FileNotFoundError):
            return {}

        dimms = []
        current: dict = {}
        for line in raw.splitlines():
            if line.startswith("Memory Device"):
                if current:
                    dimms.append(current)
                current = {}
            elif ":" in line and line.startswith("\t"):
                key, _, val = line.partition(":")
                current[key.strip()] = val.strip()
        if current:
            dimms.append(current)

        result_dimms = []
        total_bytes = 0
        ecc_enabled = False

        for d in dimms:
            size_str = d.get("Size", "No Module Installed")
            if "No Module" in size_str or "Not Installed" in size_str:
                continue
            size_bytes = _parse_dmi_size(size_str)
            total_bytes += size_bytes
            speed_str = d.get("Speed", "")
            speed_mhz = int(speed_str.split()[0]) if speed_str and speed_str[0].isdigit() else None
            ecc_str = d.get("Error Correction Type", "")
            if "ECC" in ecc_str:
                ecc_enabled = True

            result_dimms.append({
                "slot": d.get("Locator", ""),
                "size_bytes": size_bytes,
                "type": d.get("Type", ""),
                "speed_mhz": speed_mhz,
                "manufacturer": d.get("Manufacturer", ""),
                "part_number": d.get("Part Number", "").strip(),
                "ecc": "ECC" in ecc_str,
            })

        return {
            "total_bytes": total_bytes,
            "dimms": result_dimms,
            "ecc_enabled": ecc_enabled,
        }

    def _collect_dmi_type(self, dmi_type: int) -> dict:
        """Return a flat dict from a dmidecode type block."""
        try:
            raw = self._run(["dmidecode", "-t", str(dmi_type)])
        except (RuntimeError, FileNotFoundError):
            return {}
        result: dict = {}
        for line in raw.splitlines():
            if ":" in line and line.startswith("\t"):
                key, _, val = line.partition(":")
                result[key.strip()] = val.strip()
        return result


def _parse_dmi_size(s: str) -> int:
    """Convert '16384 MB' or '32 GB' to bytes."""
    parts = s.split()
    if len(parts) < 2:
        return 0
    try:
        value = int(parts[0])
    except ValueError:
        return 0
    unit = parts[1].upper()
    multipliers = {"KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    return value * multipliers.get(unit, 1)
