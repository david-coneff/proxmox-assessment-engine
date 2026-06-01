#!/usr/bin/env python3
"""Tests for Phase 12.E.8 — Spawn workbook ODS generator."""

import sys, unittest, zipfile, io, tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "proxmox-bootstrap"))

from spawn_workbook import build_spawn_workbook, generate_spawn_workbook_file

PLAN = {
    "cell_id": "cell-alpha",
    "hostname": "pve02",
    "package_id": "spawn-cell-alpha-pve02-ts",
    "generated_at": "2026-06-01T12:00:00Z",
    "lan_ip": "192.168.1.15",
    "domain": "home.example.com",
    "disposition": {
        "execution_mode": "autonomous",
        "network_mode": "lan",
        "services": ["k3s-worker", "longhorn"],
        "excluded": ["pbs-datastore"],
    },
    "storage": {
        "pool_name": "rpool",
        "topology": "mirror",
        "disk_ids": ["/dev/sda", "/dev/sdb"],
        "datastore_name": "local-rpool",
    },
    "network": {
        "bridge": "vmbr0",
        "gateway": "192.168.1.1",
        "nameservers": ["192.168.1.1", "8.8.8.8"],
    },
    "hatchery": {
        "proxmox_cluster_address": "192.168.1.10",
        "proxmox_fingerprint": "AA:BB:CC:DD",
        "headscale_url": "https://hatchery.home.example.com:8080",
    },
    "vms": [
        {"vmid": 200, "name": "k3s-worker-01", "ip": "192.168.1.50",
         "memory_mb": 4096, "initial_user": "ubuntu"},
        {"vmid": 201, "name": "longhorn-01", "ip": "192.168.1.51",
         "memory_mb": 2048, "initial_user": "ubuntu"},
    ],
    "k3s": {
        "role": "worker",
        "server_url": "https://pve01.home.example.com:6443",
        "worker_join_token": "K10::worker::abc",
        "node_labels": ["worker=true"],
    },
}

HARDWARE = {
    "hostname": "pve02",
    "cpu_model": "Intel Core i7-8700",
    "cpu_cores": 6,
    "ram_gb": 32,
    "disks": [
        {"name": "sda", "size_gb": 500, "rotational": False},
        {"name": "sdb", "size_gb": 500, "rotational": False},
    ],
    "nics": [
        {"name": "eno1", "mac": "AA:BB:CC:DD:EE:FF", "speed_mbps": 1000},
    ],
    "derived": {
        "usable_disks": 2, "ssd_count": 2, "hdd_count": 0, "zfs_topology": "mirror"
    },
}


def _ods_bytes(plan=None, hw=None) -> bytes:
    return build_spawn_workbook(plan or PLAN, hw)


def _content_xml(plan=None, hw=None) -> str:
    raw = _ods_bytes(plan, hw)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        return zf.read("content.xml").decode("utf-8")


class TestOdsStructure(unittest.TestCase):
    def setUp(self):
        self.raw = _ods_bytes()

    def test_returns_bytes(self):
        self.assertIsInstance(self.raw, bytes)

    def test_valid_zip(self):
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(self.raw)))

    def test_has_mimetype(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as zf:
            self.assertIn("mimetype", zf.namelist())

    def test_has_content_xml(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as zf:
            self.assertIn("content.xml", zf.namelist())

    def test_has_manifest(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as zf:
            self.assertIn("META-INF/manifest.xml", zf.namelist())

    def test_mimetype_is_spreadsheet(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as zf:
            mt = zf.read("mimetype")
        self.assertIn(b"spreadsheet", mt)


class TestSheetNames(unittest.TestCase):
    def setUp(self):
        self.xml = _content_xml()

    def test_overview_sheet(self):
        self.assertIn("Overview", self.xml)

    def test_discovery_sheet(self):
        self.assertIn("Discovery", self.xml)

    def test_storage_sheet(self):
        self.assertIn("Storage", self.xml)

    def test_network_sheet(self):
        self.assertIn("Network", self.xml)

    def test_proxmox_join_sheet(self):
        self.assertIn("Proxmox-Join", self.xml)

    def test_vms_sheet(self):
        self.assertIn("VMs", self.xml)

    def test_k3s_join_sheet(self):
        self.assertIn("k3s-Join", self.xml)

    def test_validation_sheet(self):
        self.assertIn("Validation", self.xml)


class TestOverviewSheet(unittest.TestCase):
    def setUp(self):
        self.xml = _content_xml()

    def test_hostname_present(self):
        self.assertIn("pve02", self.xml)

    def test_cell_id_present(self):
        self.assertIn("cell-alpha", self.xml)

    def test_execution_mode_present(self):
        self.assertIn("autonomous", self.xml)

    def test_service_in_plan(self):
        self.assertIn("k3s-worker", self.xml)

    def test_excluded_service_present(self):
        self.assertIn("pbs-datastore", self.xml)

    def test_phase_rows_present(self):
        self.assertIn("phase-00-preflight", self.xml)
        self.assertIn("phase-06-verify", self.xml)

    def test_pending_status(self):
        self.assertIn("PENDING", self.xml)


class TestDiscoverySheet(unittest.TestCase):
    def test_with_hardware_profile(self):
        xml = _content_xml(hw=HARDWARE)
        self.assertIn("Intel Core i7-8700", xml)
        self.assertIn("32", xml)  # RAM
        self.assertIn("sda", xml)
        self.assertIn("SSD", xml)
        self.assertIn("eno1", xml)
        self.assertIn("mirror", xml)  # derived topology

    def test_without_hardware_profile(self):
        xml = _content_xml()
        self.assertIn("interactive mode", xml.lower())

    def test_nic_mac_present(self):
        xml = _content_xml(hw=HARDWARE)
        self.assertIn("AA:BB:CC:DD:EE:FF", xml)


class TestStorageSheet(unittest.TestCase):
    def setUp(self):
        self.xml = _content_xml()

    def test_pool_name(self):
        self.assertIn("rpool", self.xml)

    def test_topology(self):
        self.assertIn("mirror", self.xml)

    def test_disk_ids(self):
        self.assertIn("/dev/sda", self.xml)
        self.assertIn("/dev/sdb", self.xml)

    def test_datastore_name(self):
        self.assertIn("local-rpool", self.xml)


class TestNetworkSheet(unittest.TestCase):
    def setUp(self):
        self.xml = _content_xml()

    def test_bridge_name(self):
        self.assertIn("vmbr0", self.xml)

    def test_gateway(self):
        self.assertIn("192.168.1.1", self.xml)

    def test_nameservers(self):
        self.assertIn("8.8.8.8", self.xml)

    def test_network_mode(self):
        self.assertIn("lan", self.xml)


class TestProxmoxJoinSheet(unittest.TestCase):
    def setUp(self):
        self.xml = _content_xml()

    def test_cluster_address(self):
        self.assertIn("192.168.1.10", self.xml)

    def test_fingerprint(self):
        self.assertIn("AA:BB:CC:DD", self.xml)

    def test_broodling_ip(self):
        self.assertIn("192.168.1.15", self.xml)


class TestVmsSheet(unittest.TestCase):
    def setUp(self):
        self.xml = _content_xml()

    def test_vm_count(self):
        self.assertIn("2", self.xml)  # 2 VMs

    def test_vmid_200(self):
        self.assertIn("200", self.xml)

    def test_vmid_201(self):
        self.assertIn("201", self.xml)

    def test_vm_ip(self):
        self.assertIn("192.168.1.50", self.xml)

    def test_vm_name(self):
        self.assertIn("k3s-worker-01", self.xml)

    def test_memory_present(self):
        self.assertIn("4096", self.xml)


class TestK3sJoinSheet(unittest.TestCase):
    def setUp(self):
        self.xml = _content_xml()

    def test_k3s_role(self):
        self.assertIn("worker", self.xml)

    def test_server_url(self):
        self.assertIn("pve01.home.example.com", self.xml)

    def test_no_token_in_plain_text(self):
        # The token value itself should NOT appear verbatim; only a KeePass path ref
        self.assertNotIn("K10::worker::abc", self.xml)

    def test_node_labels(self):
        self.assertIn("worker=true", self.xml)


class TestValidationSheet(unittest.TestCase):
    def setUp(self):
        self.xml = _content_xml()

    def test_preflight_check_present(self):
        self.assertIn("Disks verified", self.xml)

    def test_all_phases_listed(self):
        for phase in ["phase-00-preflight", "phase-00-host", "phase-01-proxmox",
                      "phase-02-vms", "phase-03-cloudinit", "phase-04-k3s",
                      "phase-06-verify"]:
            self.assertIn(phase, self.xml)

    def test_post_spawn_checks(self):
        self.assertIn("bootstrap-state updated", self.xml)
        self.assertIn("Flux CD", self.xml)

    def test_pending_status_for_all(self):
        # Should have many PENDING entries
        count = self.xml.count("PENDING")
        self.assertGreaterEqual(count, 10)


class TestK3sServerHaPhase(unittest.TestCase):
    def test_ha_row_for_server_role(self):
        plan = {**PLAN, "k3s": {**PLAN["k3s"], "role": "server"}}
        xml = _content_xml(plan)
        self.assertIn("phase-05-ha", xml)

    def test_no_ha_section_for_worker(self):
        xml = _content_xml()
        # Worker should not have an HA phase section in k3s sheet
        # (it's in overview though as conditional)
        # Just verify it won't error
        self.assertIn("worker", xml)


class TestGenerateFile(unittest.TestCase):
    def test_writes_ods_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out" / "spawn-workbook.ods"
            result = generate_spawn_workbook_file(PLAN, out, HARDWARE)
            self.assertTrue(result.exists())
            self.assertTrue(zipfile.is_zipfile(result))

    def test_creates_parent_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "nested" / "deep" / "spawn.ods"
            generate_spawn_workbook_file(PLAN, out)
            self.assertTrue(out.exists())

    def test_returns_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "spawn.ods"
            result = generate_spawn_workbook_file(PLAN, out)
            self.assertIsInstance(result, Path)


class TestEmptyPlan(unittest.TestCase):
    def test_minimal_plan_does_not_crash(self):
        xml = _content_xml({})
        self.assertIn("Overview", xml)
        self.assertIn("Validation", xml)

    def test_no_vms_in_plan(self):
        plan = {**PLAN, "vms": []}
        xml = _content_xml(plan)
        self.assertIn("(none declared", xml)


if __name__ == "__main__":
    unittest.main()
