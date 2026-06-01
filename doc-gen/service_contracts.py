#!/usr/bin/env python3
"""
service_contracts.py — Service contract registry and validator for doc-gen.

Provides:
  ServiceContractRegistry  — fast lookups over declared service contracts
  ServiceContractValidator — compares declared contracts against observed VM state
  build_service_contract_registry(manifest) — factory from manifest dict

Data is sourced from manifest["service_contracts"] injected by engine.py
from bootstrap-state.json (which mirrors proxmox-bootstrap/service-contracts.yaml).
"""

from typing import Optional


# ---------------------------------------------------------------------------
# ServiceContractRegistry
# ---------------------------------------------------------------------------

class ServiceContractRegistry:
    """
    Wrapper around the service_contracts list for fast lookups.

    Contracts are keyed by service id (str). Each VM may have multiple
    contracts (one per service it hosts, though usually one).
    """

    def __init__(self, contracts: list):
        self._contracts = list(contracts or [])
        self._by_service: dict[str, dict] = {}
        self._by_vm: dict[str, list] = {}

        for c in self._contracts:
            svc = c.get("service")
            vm  = c.get("vm")
            if svc:
                self._by_service[svc] = c
            if vm:
                self._by_vm.setdefault(vm, []).append(c)

    def available(self) -> bool:
        return bool(self._contracts)

    def count(self) -> int:
        return len(self._contracts)

    def get(self, service_id: str) -> Optional[dict]:
        """Return contract for the given service id, or None."""
        return self._by_service.get(service_id)

    def for_vm(self, vm_name: str) -> list:
        """Return all contracts for a given VM name."""
        return list(self._by_vm.get(vm_name, []))

    def all(self) -> list:
        return list(self._contracts)

    def service_ids(self) -> list:
        return list(self._by_service.keys())

    def vm_names(self) -> list:
        return list(self._by_vm.keys())

    def dependency_pairs(self) -> list:
        """
        Return (consumer_vm, provider_vm, label) triples derived from
        required_interfaces declarations.

        Only pairs where both VMs have declared contracts are included.
        label is "{service} ({protocol}:{port})".
        """
        pairs = []
        for c in self._contracts:
            consumer_vm = c.get("vm")
            if not consumer_vm:
                continue
            for req in c.get("required_interfaces") or []:
                provider_svc = req.get("service")
                if not provider_svc:
                    continue
                provider_contract = self._by_service.get(provider_svc)
                if not provider_contract:
                    continue
                provider_vm = provider_contract.get("vm")
                if provider_vm and provider_vm != consumer_vm:
                    label = (f"{provider_svc} "
                             f"({req.get('protocol', '?')}:{req.get('port', '?')})")
                    pairs.append((consumer_vm, provider_vm, label))
        return pairs

    def startup_order_pairs(self) -> list:
        """
        Return (consumer_vm, provider_vm, label) triples derived from
        startup_after declarations.

        Only pairs where both VMs have declared contracts are included.
        """
        pairs = []
        for c in self._contracts:
            consumer_vm = c.get("vm")
            if not consumer_vm:
                continue
            for svc in c.get("startup_after") or []:
                provider_contract = self._by_service.get(svc)
                if not provider_contract:
                    continue
                provider_vm = provider_contract.get("vm")
                if provider_vm and provider_vm != consumer_vm:
                    pairs.append((consumer_vm, provider_vm, f"starts after {svc}"))
        return pairs


# ---------------------------------------------------------------------------
# ServiceContractValidator
# ---------------------------------------------------------------------------

class ServiceContractValidator:
    """
    Validates declared service contracts against observed VM state.

    Findings describe mismatches between what is declared and what is running.
    Does not attempt network connectivity checks — only structural validation.
    """

    def __init__(self, registry: ServiceContractRegistry):
        self._registry = registry

    def validate(self, vm_list: list) -> list:
        """
        Compare declared contracts against observed VM state.

        vm_list: list of VM dicts from manifest.vms (each has vmid, name, status).
        Returns list of finding dicts:
          {service, vm, severity, issue, remediation}
        Severity: RED (service broken), YELLOW (degraded or missing contract).
        """
        findings = []

        # Index observed VMs: name → status
        observed: dict[str, str] = {}
        for vm in vm_list:
            name   = vm.get("name", "")
            status = vm.get("status", "")
            if name:
                observed[name] = status

        running: set = {n for n, s in observed.items() if s == "running"}

        for contract in self._registry.all():
            svc     = contract.get("service", "?")
            vm_name = contract.get("vm")

            if not vm_name:
                continue

            # VM not in observed manifest at all
            if vm_name not in observed:
                findings.append({
                    "service":     svc,
                    "vm":          vm_name,
                    "severity":    "YELLOW",
                    "issue":       (f"VM '{vm_name}' for service '{svc}' "
                                    f"is not present in observed inventory"),
                    "remediation": (f"Verify VM '{vm_name}' exists on Proxmox host; "
                                    f"run Tier 2 collection to refresh inventory"),
                })
                continue

            # VM exists but not running
            if vm_name not in running:
                findings.append({
                    "service":     svc,
                    "vm":          vm_name,
                    "severity":    "RED",
                    "issue":       (f"VM '{vm_name}' for service '{svc}' "
                                    f"is present but not running "
                                    f"(status: {observed[vm_name]!r})"),
                    "remediation": f"Start VM '{vm_name}': qm start {contract.get('vmid', '?')}",
                })
                continue

            # VM is running — check required interfaces
            for req in contract.get("required_interfaces") or []:
                provider_svc = req.get("service")
                critical     = req.get("critical", False)
                if not provider_svc:
                    continue

                provider_contract = self._registry.get(provider_svc)
                if not provider_contract:
                    # Required service has no declared contract
                    if critical:
                        findings.append({
                            "service":     svc,
                            "vm":          vm_name,
                            "severity":    "YELLOW",
                            "issue":       (f"Service '{svc}' requires '{provider_svc}' "
                                            f"(critical) but '{provider_svc}' has no "
                                            f"declared service contract"),
                            "remediation": (f"Add a service contract for '{provider_svc}' "
                                            f"in service-contracts.yaml"),
                        })
                    continue

                provider_vm = provider_contract.get("vm")
                if not provider_vm:
                    continue

                if provider_vm not in running:
                    severity = "RED" if critical else "YELLOW"
                    status   = observed.get(provider_vm, "absent")
                    findings.append({
                        "service":     svc,
                        "vm":          vm_name,
                        "severity":    severity,
                        "issue":       (f"Service '{svc}' requires '{provider_svc}' "
                                        f"({'critical' if critical else 'non-critical'}) "
                                        f"but provider VM '{provider_vm}' is not running "
                                        f"(status: {status!r})"),
                        "remediation": (f"Start '{provider_vm}' before '{vm_name}'; "
                                        f"startup order: {provider_svc} → {svc}"),
                    })

        return findings


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_service_contract_registry(manifest: dict) -> ServiceContractRegistry:
    """
    Build a ServiceContractRegistry from manifest["service_contracts"].

    engine.py injects this key from bootstrap-state.json.
    Returns an empty registry (available() == False) if key is absent.
    """
    contracts = manifest.get("service_contracts") or []
    return ServiceContractRegistry(contracts)
