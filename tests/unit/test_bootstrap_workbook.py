#!/usr/bin/env python3
"""
Tests for doc-gen/renderers/workbook.py — build_bootstrap_workbook().

Verifies that Stage 03 fields are pre-populated from the DNS and template
registries when bootstrap-state.json data is available in the manifest, and
fall back to HUMAN prompts when registries are absent.
"""

import io
import sys
import unittest
import zipfile
from pathlib import Path

# Ensure doc-gen and doc-gen/renderers are importable
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "doc-gen"))
sys.path.insert(0, str(REPO_ROOT / "doc-gen" / "renderers"))

from workbook import (
    build_bootstrap_workbook,
    _registry_ip_for_bootstrap_vm,
    _registry_iso_path,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DNS_ENTRIES = [
    {"hostname": "pve01.internal", "ip": "192.168.1.10", "vmid": None, "role": "proxmox-host"},
    {"hostname": "infra-bootstrap.internal", "ip": "192.168.1.20", "vmid": 100,
     "role": "infra-bootstrap"},
    {"hostname": "forgejo.internal", "ip": "192.168.1.21", "vmid": 101, "role": "forgejo"},
]

BASE_IMAGES = [
    {
        "name": "ubuntu-2204-base",
        "source_iso": "ubuntu-22.04.4-live-server-amd64.iso",
        "source_url": "https://releases.ubuntu.com/22.04/ubuntu-22.04.4-live-server-amd64.iso",
        "checksum": "sha256:abc123",
        "created_at": "2026-04-01T10:00:00Z",
    }
]

STORAGE_CONFIG = {
    "snippets": "local:snippets",
    "isos": "local:iso",
    "vm_disks": "local-zfs",
}

MINIMAL_MANIFEST = {
    "host": {"hostname": "pve01", "fqdn": "pve01.internal"},
}

FULL_MANIFEST = {
    "host": {"hostname": "pve01", "fqdn": "pve01.internal"},
    "dns_registry": DNS_ENTRIES,
    "base_images": BASE_IMAGES,
    "bootstrap_state_storage": STORAGE_CONFIG,
}

EMPTY_RESOLVED = {}
EMPTY_META = {"field_counts": {"AUTO": 0, "DERIVED": 0, "HUMAN": 0, "UNRESOLVED": 0}}


def _extract_content_xml(ods_bytes: bytes) -> str:
    """Extract content.xml text from an ODS byte stream."""
    buf = io.BytesIO(ods_bytes)
    with zipfile.ZipFile(buf, "r") as zf:
        return zf.read("content.xml").decode("utf-8")


# ---------------------------------------------------------------------------
# _registry_ip_for_bootstrap_vm
# ---------------------------------------------------------------------------

class TestRegistryIpForBootstrapVm(unittest.TestCase):

    def test_returns_ip_by_role(self):
        manifest = {"dns_registry": DNS_ENTRIES}
        self.assertEqual(_registry_ip_for_bootstrap_vm(manifest), "192.168.1.20")

    def test_returns_ip_by_hostname_prefix(self):
        entries = [{"hostname": "infra-bootstrap.internal", "ip": "10.0.0.5",
                    "vmid": None, "role": "other"}]
        manifest = {"dns_registry": entries}
        self.assertEqual(_registry_ip_for_bootstrap_vm(manifest), "10.0.0.5")

    def test_fallback_to_vmid_100(self):
        entries = [{"hostname": "bootstrap.internal", "ip": "10.0.0.9",
                    "vmid": 100, "role": "custom-role"}]
        manifest = {"dns_registry": entries}
        self.assertEqual(_registry_ip_for_bootstrap_vm(manifest), "10.0.0.9")

    def test_returns_none_when_no_registry(self):
        self.assertIsNone(_registry_ip_for_bootstrap_vm({}))

    def test_returns_none_when_empty_registry(self):
        self.assertIsNone(_registry_ip_for_bootstrap_vm({"dns_registry": []}))

    def test_returns_none_when_no_matching_entry(self):
        entries = [{"hostname": "forgejo.internal", "ip": "192.168.1.21",
                    "vmid": 101, "role": "forgejo"}]
        self.assertIsNone(_registry_ip_for_bootstrap_vm({"dns_registry": entries}))

    def test_skips_entry_with_no_ip(self):
        entries = [
            {"hostname": "infra-bootstrap.internal", "ip": None, "vmid": 100,
             "role": "infra-bootstrap"},
            {"hostname": "infra-bootstrap-v2.internal", "ip": "10.0.0.99",
             "vmid": 200, "role": "infra-bootstrap"},
        ]
        # First entry has no IP — should fall through to second
        result = _registry_ip_for_bootstrap_vm({"dns_registry": entries})
        self.assertEqual(result, "10.0.0.99")


# ---------------------------------------------------------------------------
# _registry_iso_path
# ---------------------------------------------------------------------------

class TestRegistryIsoPath(unittest.TestCase):

    def test_builds_path_from_base_image_and_storage(self):
        manifest = {"base_images": BASE_IMAGES, "bootstrap_state_storage": STORAGE_CONFIG}
        self.assertEqual(_registry_iso_path(manifest),
                         "local:iso/ubuntu-22.04.4-live-server-amd64.iso")

    def test_defaults_isos_store_when_storage_config_absent(self):
        manifest = {"base_images": BASE_IMAGES}
        result = _registry_iso_path(manifest)
        self.assertEqual(result, "local:iso/ubuntu-22.04.4-live-server-amd64.iso")

    def test_uses_storage_config_key(self):
        manifest = {
            "base_images": BASE_IMAGES,
            "bootstrap_state_storage": {"isos": "cephfs:iso"},
        }
        self.assertEqual(_registry_iso_path(manifest),
                         "cephfs:iso/ubuntu-22.04.4-live-server-amd64.iso")

    def test_returns_none_when_no_base_images(self):
        self.assertIsNone(_registry_iso_path({}))
        self.assertIsNone(_registry_iso_path({"base_images": []}))

    def test_returns_none_when_source_iso_missing(self):
        manifest = {"base_images": [{"name": "ubuntu-2204-base"}]}
        self.assertIsNone(_registry_iso_path(manifest))


# ---------------------------------------------------------------------------
# build_bootstrap_workbook — Stage 03 registry pre-population
# ---------------------------------------------------------------------------

class TestBuildBootstrapWorkbookStage03(unittest.TestCase):

    def _content(self, manifest):
        ods = build_bootstrap_workbook(manifest, EMPTY_RESOLVED, EMPTY_META)
        return _extract_content_xml(ods)

    def test_returns_valid_ods_bytes_with_full_manifest(self):
        ods = build_bootstrap_workbook(FULL_MANIFEST, EMPTY_RESOLVED, EMPTY_META)
        self.assertIsInstance(ods, bytes)
        self.assertTrue(len(ods) > 0)
        buf = io.BytesIO(ods)
        with zipfile.ZipFile(buf, "r") as zf:
            self.assertIn("content.xml", zf.namelist())

    def test_ip_pre_populated_from_dns_registry(self):
        content = self._content(FULL_MANIFEST)
        self.assertIn("192.168.1.20", content)

    def test_ip_field_class_is_auto_when_registry_present(self):
        content = self._content(FULL_MANIFEST)
        # AUTO class means the field was populated from the registry
        self.assertIn("[AUTO]", content)

    def test_iso_path_pre_populated_from_template_registry(self):
        content = self._content(FULL_MANIFEST)
        self.assertIn("local:iso/ubuntu-22.04.4-live-server-amd64.iso", content)

    def test_iso_field_class_is_derived_when_registry_present(self):
        content = self._content(FULL_MANIFEST)
        self.assertIn("[DERIVED]", content)

    def test_ssh_checkpoint_uses_real_ip(self):
        content = self._content(FULL_MANIFEST)
        self.assertIn("ssh ubuntu@192.168.1.20", content)
        self.assertNotIn("ssh ubuntu@[VM_IP]", content)

    def test_qm_create_note_references_ip(self):
        content = self._content(FULL_MANIFEST)
        self.assertIn("192.168.1.20", content)
        self.assertNotIn("Replace [VM_IP]", content)

    # Fallback behaviour when registries absent

    def test_ip_falls_back_to_human_field_without_registry(self):
        content = self._content(MINIMAL_MANIFEST)
        self.assertIn("[HUMAN]", content)

    def test_ssh_checkpoint_uses_placeholder_without_registry(self):
        content = self._content(MINIMAL_MANIFEST)
        self.assertIn("[VM_IP]", content)

    def test_iso_falls_back_to_human_field_without_registry(self):
        content = self._content(MINIMAL_MANIFEST)
        # HUMAN field should appear for ISO path
        self.assertIn("[HUMAN]", content)

    def test_no_crash_with_empty_dns_registry(self):
        manifest = {**MINIMAL_MANIFEST, "dns_registry": []}
        ods = build_bootstrap_workbook(manifest, EMPTY_RESOLVED, EMPTY_META)
        self.assertIsInstance(ods, bytes)

    def test_no_crash_with_empty_base_images(self):
        manifest = {**MINIMAL_MANIFEST, "base_images": []}
        ods = build_bootstrap_workbook(manifest, EMPTY_RESOLVED, EMPTY_META)
        self.assertIsInstance(ods, bytes)

    def test_partial_registry_dns_only(self):
        manifest = {**MINIMAL_MANIFEST, "dns_registry": DNS_ENTRIES}
        content = self._content(manifest)
        # IP populated, ISO still HUMAN
        self.assertIn("192.168.1.20", content)
        self.assertIn("[HUMAN]", content)

    def test_partial_registry_templates_only(self):
        manifest = {
            **MINIMAL_MANIFEST,
            "base_images": BASE_IMAGES,
            "bootstrap_state_storage": STORAGE_CONFIG,
        }
        content = self._content(manifest)
        # ISO populated, IP still [VM_IP]
        self.assertIn("local:iso/ubuntu-22.04.4-live-server-amd64.iso", content)
        self.assertIn("[VM_IP]", content)


# ---------------------------------------------------------------------------
# build_bootstrap_workbook — ODS structure integrity
# ---------------------------------------------------------------------------

class TestBuildBootstrapWorkbookStructure(unittest.TestCase):

    def test_ods_contains_required_sheets(self):
        ods = build_bootstrap_workbook(MINIMAL_MANIFEST, EMPTY_RESOLVED, EMPTY_META)
        content = _extract_content_xml(ods)
        self.assertIn("Stage 01", content)
        self.assertIn("Stage 02", content)
        self.assertIn("Stage 03", content)
        self.assertIn("Generation Report", content)

    def test_ods_mimetype_is_correct(self):
        ods = build_bootstrap_workbook(MINIMAL_MANIFEST, EMPTY_RESOLVED, EMPTY_META)
        buf = io.BytesIO(ods)
        with zipfile.ZipFile(buf, "r") as zf:
            mimetype = zf.read("mimetype")
        self.assertEqual(mimetype, b"application/vnd.oasis.opendocument.spreadsheet")


if __name__ == "__main__":
    unittest.main()
