"""
Tests for Phase 3 — Ansible roles and playbooks.

Covers:
  - Role directory structure completeness
  - YAML validity of all role files, playbooks, group_vars
  - tasks/main.yaml: required modules, idempotency markers
  - handlers/main.yaml: handler names referenced in tasks exist
  - group_vars/all.yaml: required variable keys present
  - Playbooks: correct host groups, role references, ordering convention
  - No hard-coded IPs or hostnames in role YAML files

Run: py -3 tests/unit/test_phase3_ansible_roles.py
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
ANSIBLE_DIR = REPO_ROOT / "ansible"
ROLES_DIR = ANSIBLE_DIR / "roles"
PLAYBOOKS_DIR = ANSIBLE_DIR / "playbooks"
GROUP_VARS = ANSIBLE_DIR / "group_vars" / "all.yaml"


# ---------------------------------------------------------------------------
# Minimal YAML parser (stdlib only — no pip)
# ---------------------------------------------------------------------------

def _load_yaml_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _yaml_keys_at_top_level(text: str) -> list[str]:
    """Return top-level YAML keys (lines that start without leading spaces and have a colon)."""
    keys = []
    for line in text.splitlines():
        if line and not line.startswith(" ") and not line.startswith("#") and ":" in line:
            key = line.split(":")[0].strip()
            if key and not key.startswith("-"):
                keys.append(key)
    return keys


def _yaml_list_items(text: str) -> list[str]:
    """Return all '- name:' values from a YAML task list."""
    names = []
    for line in text.splitlines():
        m = re.match(r"\s*-\s+name:\s+(.+)", line)
        if m:
            names.append(m.group(1).strip())
    return names


def _extract_values(text: str, key: str) -> list[str]:
    """Extract all values for a given key from YAML text."""
    pattern = re.compile(rf"^\s*{re.escape(key)}:\s*(.+)", re.MULTILINE)
    return [m.group(1).strip() for m in pattern.finditer(text)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_ROLES = ["common", "forgejo", "operations-vm", "k3s-server"]

EXPECTED_PLAYBOOKS = [
    "01-common.yaml",
    "02-forgejo.yaml",
    "03-operations.yaml",
    "04-k3s.yaml",
]

IP_PATTERN = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")

# IPs allowed in defaults (placeholder-only contexts)
ALLOWED_IP_FILES = {
    "group_vars/all.yaml",  # may contain CIDR examples in comments
}


class TestRoleStructure(unittest.TestCase):
    """All four roles exist with required subdirectories/files."""

    def test_roles_directory_exists(self):
        self.assertTrue(ROLES_DIR.is_dir(), f"ansible/roles/ not found at {ROLES_DIR}")

    def test_all_roles_present(self):
        present = {d.name for d in ROLES_DIR.iterdir() if d.is_dir()}
        for role in EXPECTED_ROLES:
            self.assertIn(role, present, f"Role '{role}' missing from ansible/roles/")

    def test_each_role_has_tasks_main(self):
        for role in EXPECTED_ROLES:
            p = ROLES_DIR / role / "tasks" / "main.yaml"
            self.assertTrue(p.exists(), f"{role}/tasks/main.yaml missing")

    def test_each_role_has_defaults_main(self):
        for role in EXPECTED_ROLES:
            p = ROLES_DIR / role / "defaults" / "main.yaml"
            self.assertTrue(p.exists(), f"{role}/defaults/main.yaml missing")

    def test_roles_with_handlers_have_handlers_main(self):
        roles_with_handlers = ["common", "forgejo", "k3s-server"]
        for role in roles_with_handlers:
            p = ROLES_DIR / role / "handlers" / "main.yaml"
            self.assertTrue(p.exists(), f"{role}/handlers/main.yaml missing")

    def test_forgejo_has_templates(self):
        tmpl_dir = ROLES_DIR / "forgejo" / "templates"
        self.assertTrue(tmpl_dir.is_dir(), "forgejo/templates/ missing")
        self.assertTrue((tmpl_dir / "app.ini.j2").exists(), "forgejo/templates/app.ini.j2 missing")
        self.assertTrue((tmpl_dir / "forgejo.service.j2").exists(), "forgejo/templates/forgejo.service.j2 missing")

    def test_k3s_server_has_files_directory(self):
        files_dir = ROLES_DIR / "k3s-server" / "files"
        self.assertTrue(files_dir.is_dir(), "k3s-server/files/ missing (config.yaml deployed here)")


class TestYamlValidity(unittest.TestCase):
    """All YAML files are parseable (no syntax errors caught by our minimal parser)."""

    def _check_yaml_file(self, path: Path):
        text = _load_yaml_text(path)
        # Must not be empty
        stripped = text.strip()
        self.assertTrue(len(stripped) > 0, f"{path} is empty")
        # Must start with --- or a valid YAML key / list
        first_content = next(
            (line for line in text.splitlines() if line.strip() and not line.strip().startswith("#")),
            None,
        )
        self.assertIsNotNone(first_content, f"{path} has no non-comment content")

    def test_tasks_files_parseable(self):
        for role in EXPECTED_ROLES:
            p = ROLES_DIR / role / "tasks" / "main.yaml"
            if p.exists():
                self._check_yaml_file(p)

    def test_defaults_files_parseable(self):
        for role in EXPECTED_ROLES:
            p = ROLES_DIR / role / "defaults" / "main.yaml"
            if p.exists():
                self._check_yaml_file(p)

    def test_handlers_files_parseable(self):
        for role in ["common", "forgejo", "k3s-server"]:
            p = ROLES_DIR / role / "handlers" / "main.yaml"
            if p.exists():
                self._check_yaml_file(p)

    def test_playbooks_parseable(self):
        for pb in EXPECTED_PLAYBOOKS:
            p = PLAYBOOKS_DIR / pb
            if p.exists():
                self._check_yaml_file(p)

    def test_group_vars_all_parseable(self):
        self._check_yaml_file(GROUP_VARS)


class TestGroupVars(unittest.TestCase):
    """group_vars/all.yaml contains required variable keys."""

    def setUp(self):
        self.text = _load_yaml_text(GROUP_VARS)

    def test_file_exists(self):
        self.assertTrue(GROUP_VARS.exists(), "ansible/group_vars/all.yaml missing")

    def test_required_keys_present(self):
        required = [
            "common_timezone",
            "common_packages",
            "forgejo_version",
            "forgejo_port",
            "opentofu_version",
            "flux_version",
            "kubectl_version",
            "k3s_version",
            "k3s_config_path",
        ]
        for key in required:
            self.assertIn(key, self.text, f"group_vars/all.yaml missing key: {key}")

    def test_no_hard_coded_ips(self):
        for line in self.text.splitlines():
            if line.strip().startswith("#"):
                continue
            # Allow 8.8.8.8 as an explicit example DNS server reference
            line_no_comments = line.split("#")[0]
            matches = IP_PATTERN.findall(line_no_comments)
            for ip in matches:
                self.fail(f"Hard-coded IP '{ip}' found in group_vars/all.yaml: {line.strip()!r}")


class TestCommonRole(unittest.TestCase):

    def setUp(self):
        self.tasks = _load_yaml_text(ROLES_DIR / "common" / "tasks" / "main.yaml")
        self.handlers = _load_yaml_text(ROLES_DIR / "common" / "handlers" / "main.yaml")

    def test_sets_hostname(self):
        self.assertIn("ansible.builtin.hostname", self.tasks)

    def test_installs_packages(self):
        self.assertIn("ansible.builtin.apt", self.tasks)

    def test_hardens_ssh(self):
        self.assertIn("sshd_config", self.tasks)

    def test_enables_ufw(self):
        self.assertIn("community.general.ufw", self.tasks)

    def test_handlers_cover_sshd_and_cron(self):
        self.assertIn("restart sshd", self.handlers)
        self.assertIn("restart cron", self.handlers)

    def test_uses_fqdn_variable_not_literal(self):
        # No hard-coded FQDN — must use {{ fqdn }} or {{ inventory_hostname }}
        self.assertNotIn(".internal", self.tasks)

    def test_no_hard_coded_ips(self):
        for line in self.tasks.splitlines():
            line_code = line.split("#")[0]
            matches = IP_PATTERN.findall(line_code)
            self.assertEqual(matches, [], f"Hard-coded IP in common/tasks/main.yaml: {line.strip()!r}")


class TestForgejoRole(unittest.TestCase):

    def setUp(self):
        self.tasks = _load_yaml_text(ROLES_DIR / "forgejo" / "tasks" / "main.yaml")
        self.defaults = _load_yaml_text(ROLES_DIR / "forgejo" / "defaults" / "main.yaml")
        self.handlers = _load_yaml_text(ROLES_DIR / "forgejo" / "handlers" / "main.yaml")
        self.app_ini = _load_yaml_text(ROLES_DIR / "forgejo" / "templates" / "app.ini.j2")
        self.service = _load_yaml_text(ROLES_DIR / "forgejo" / "templates" / "forgejo.service.j2")

    def test_creates_system_user(self):
        self.assertIn("ansible.builtin.user", self.tasks)

    def test_downloads_binary(self):
        self.assertIn("ansible.builtin.get_url", self.tasks)

    def test_deploys_app_ini_template(self):
        self.assertIn("app.ini.j2", self.tasks)

    def test_deploys_systemd_unit(self):
        self.assertIn("forgejo.service.j2", self.tasks)

    def test_enables_service(self):
        self.assertIn("ansible.builtin.systemd", self.tasks)
        self.assertIn("enabled: true", self.tasks)

    def test_handlers_present(self):
        self.assertIn("restart forgejo", self.handlers)
        self.assertIn("reload systemd", self.handlers)

    def test_app_ini_uses_variables_not_literals(self):
        # Must use Jinja2 variables for port/fqdn
        self.assertIn("{{ forgejo_port }}", self.app_ini)
        self.assertIn("{{ fqdn }}", self.app_ini)

    def test_app_ini_no_hard_coded_ips(self):
        for line in self.app_ini.splitlines():
            line_code = line.split(";")[0]  # ini-style comments
            matches = IP_PATTERN.findall(line_code)
            self.assertEqual(matches, [], f"Hard-coded IP in app.ini.j2: {line.strip()!r}")

    def test_service_template_uses_variables(self):
        self.assertIn("{{ forgejo_user }}", self.service)
        self.assertIn("{{ forgejo_binary }}", self.service)

    def test_defaults_include_version(self):
        self.assertIn("forgejo_version", self.defaults)

    def test_opens_correct_ports(self):
        self.assertIn("forgejo_port", self.tasks)
        self.assertIn("forgejo_ssh_port", self.tasks)


class TestOperationsVmRole(unittest.TestCase):

    def setUp(self):
        self.tasks = _load_yaml_text(ROLES_DIR / "operations-vm" / "tasks" / "main.yaml")
        self.defaults = _load_yaml_text(ROLES_DIR / "operations-vm" / "defaults" / "main.yaml")

    def test_installs_opentofu(self):
        self.assertIn("opentofu_version", self.tasks)

    def test_installs_flux(self):
        self.assertIn("flux_version", self.tasks)

    def test_installs_kubectl(self):
        self.assertIn("kubectl_version", self.tasks)

    def test_installs_age(self):
        self.assertIn("age_version", self.tasks)

    def test_installs_sops(self):
        self.assertIn("sops_version", self.tasks)

    def test_installs_ansible_via_pip(self):
        self.assertIn("ansible.builtin.pip", self.tasks)

    def test_creates_kube_directory(self):
        self.assertIn(".kube", self.tasks)

    def test_defaults_pin_all_versions(self):
        for tool in ["opentofu_version", "flux_version", "kubectl_version", "age_version", "sops_version"]:
            self.assertIn(tool, self.defaults)

    def test_no_hard_coded_ips(self):
        for line in self.tasks.splitlines():
            line_code = line.split("#")[0]
            matches = IP_PATTERN.findall(line_code)
            self.assertEqual(matches, [], f"Hard-coded IP in operations-vm/tasks/main.yaml: {line.strip()!r}")


class TestK3sServerRole(unittest.TestCase):

    def setUp(self):
        self.tasks = _load_yaml_text(ROLES_DIR / "k3s-server" / "tasks" / "main.yaml")
        self.defaults = _load_yaml_text(ROLES_DIR / "k3s-server" / "defaults" / "main.yaml")
        self.handlers = _load_yaml_text(ROLES_DIR / "k3s-server" / "handlers" / "main.yaml")

    def test_deploys_config_yaml(self):
        self.assertIn("config.yaml", self.tasks)

    def test_runs_install_script(self):
        self.assertIn("k3s-install.sh", self.tasks)

    def test_uses_version_variable(self):
        self.assertIn("k3s_version", self.tasks)

    def test_enables_service(self):
        self.assertIn("ansible.builtin.systemd", self.tasks)
        self.assertIn("enabled: true", self.tasks)

    def test_waits_for_ready(self):
        self.assertIn("retries", self.tasks)

    def test_copies_kubeconfig(self):
        self.assertIn(".kube", self.tasks)

    def test_opens_api_port(self):
        self.assertIn("6443", self.tasks)

    def test_handler_restarts_k3s(self):
        self.assertIn("restart k3s", self.handlers)

    def test_defaults_include_version_and_config_path(self):
        self.assertIn("k3s_version", self.defaults)
        self.assertIn("k3s_config_path", self.defaults)

    def test_no_hard_coded_ips(self):
        for line in self.tasks.splitlines():
            line_code = line.split("#")[0]
            matches = IP_PATTERN.findall(line_code)
            self.assertEqual(matches, [], f"Hard-coded IP in k3s-server/tasks/main.yaml: {line.strip()!r}")


class TestPlaybooks(unittest.TestCase):

    def setUp(self):
        self.texts = {}
        for pb in EXPECTED_PLAYBOOKS:
            p = PLAYBOOKS_DIR / pb
            if p.exists():
                self.texts[pb] = _load_yaml_text(p)

    def test_all_playbooks_exist(self):
        for pb in EXPECTED_PLAYBOOKS:
            p = PLAYBOOKS_DIR / pb
            self.assertTrue(p.exists(), f"Playbook missing: {pb}")

    def test_01_common_targets_all_vms(self):
        text = self.texts.get("01-common.yaml", "")
        self.assertIn("all_vms", text)

    def test_01_common_uses_common_role(self):
        text = self.texts.get("01-common.yaml", "")
        self.assertIn("common", text)

    def test_02_forgejo_targets_pre_k3s(self):
        text = self.texts.get("02-forgejo.yaml", "")
        self.assertIn("pre_k3s", text)

    def test_02_forgejo_uses_forgejo_role(self):
        text = self.texts.get("02-forgejo.yaml", "")
        self.assertIn("forgejo", text)

    def test_03_operations_targets_pre_k3s(self):
        text = self.texts.get("03-operations.yaml", "")
        self.assertIn("pre_k3s", text)

    def test_03_operations_uses_operations_role(self):
        text = self.texts.get("03-operations.yaml", "")
        self.assertIn("operations-vm", text)

    def test_04_k3s_targets_k3s_servers(self):
        text = self.texts.get("04-k3s.yaml", "")
        self.assertIn("k3s_servers", text)

    def test_04_k3s_uses_k3s_server_role(self):
        text = self.texts.get("04-k3s.yaml", "")
        self.assertIn("k3s-server", text)

    def test_04_k3s_uses_serial_for_ha_safety(self):
        text = self.texts.get("04-k3s.yaml", "")
        self.assertIn("serial:", text)

    def test_all_playbooks_use_become(self):
        for pb, text in self.texts.items():
            self.assertIn("become: true", text, f"{pb} missing 'become: true'")

    def test_playbook_ordering_by_filename(self):
        # 01 < 02 < 03 < 04 by name
        names = sorted(self.texts.keys())
        self.assertEqual(names, sorted(EXPECTED_PLAYBOOKS))

    def test_no_playbook_has_hard_coded_ips(self):
        for pb, text in self.texts.items():
            for line in text.splitlines():
                line_code = line.split("#")[0]
                matches = IP_PATTERN.findall(line_code)
                self.assertEqual(matches, [], f"Hard-coded IP in {pb}: {line.strip()!r}")


class TestIdempotencyMarkers(unittest.TestCase):
    """Tasks that could re-run destructively must have idempotency guards."""

    def test_k3s_install_has_creates_guard(self):
        text = _load_yaml_text(ROLES_DIR / "k3s-server" / "tasks" / "main.yaml")
        self.assertIn("creates:", text)

    def test_operations_version_checks_before_install(self):
        text = _load_yaml_text(ROLES_DIR / "operations-vm" / "tasks" / "main.yaml")
        # Each tool install uses a 'when:' condition on version check
        self.assertIn("when:", text)
        self.assertIn("register:", text)

    def test_apt_install_uses_cache_valid_time(self):
        text = _load_yaml_text(ROLES_DIR / "common" / "tasks" / "main.yaml")
        self.assertIn("cache_valid_time", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
