"""
tests/unit/test_version_stamp.py — Unit tests for version_stamp.py

Covers: schema loading, _parse_schema_builtin, HashRules extraction,
_should_include, compute_codebase_hash, generate_stamp, CLI flags.
"""
from __future__ import annotations

import hashlib
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "proxmox-bootstrap"))
from version_stamp import (
    HashRules,
    _parse_schema_builtin,
    _rules_from_schema,
    _load_schema,
    _schema_path,
    _should_include,
    compute_codebase_hash,
    generate_stamp,
    main,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MINIMAL_SCHEMA = {
    "schema_version": 1,
    "hash": {"algorithm": "sha256", "truncate_chars": 8},
    "include": {"extensions": [{"ext": ".py"}, {"ext": ".sh"}, {"ext": ".yaml"},
                                {"ext": ".yml"}, {"ext": ".toml"}, {"ext": ".bats"}]},
    "exclude": {
        "extensions": [{"ext": ".md"}, {"ext": ".html"}, {"ext": ".pdf"},
                       {"ext": ".txt"}, {"ext": ".png"}, {"ext": ".jpg"},
                       {"ext": ".jpeg"}, {"ext": ".gif"}, {"ext": ".svg"},
                       {"ext": ".ico"}, {"ext": ".zip"}, {"ext": ".tar"},
                       {"ext": ".gz"}, {"ext": ".bz2"}],
        "directories": [
            {"name": ".git"}, {"name": ".ai"}, {"name": "pap"},
            {"name": "docs"}, {"name": "__pycache__"}, {"name": ".pytest_cache"},
            {"name": ".mypy_cache"}, {"name": ".ruff_cache"},
            {"name": "node_modules"},
        ],
    },
}


@pytest.fixture()
def rules() -> HashRules:
    return _rules_from_schema(_MINIMAL_SCHEMA)


def _make_schema_file(repo_root: Path) -> None:
    """Write the minimal schema into the expected location."""
    schema_dir = repo_root / "proxmox-bootstrap"
    schema_dir.mkdir(exist_ok=True)
    import yaml  # may raise ImportError — but tests using this fixture need yaml or the builtin parser
    schema_path = schema_dir / "version-hash-schema.yaml"
    # Write as a simple YAML that the builtin parser can also handle
    lines = [
        "schema_version: 1\n",
        "hash:\n",
        "  algorithm: sha256\n",
        "  truncate_chars: 8\n",
        "include:\n",
        "  extensions:\n",
    ]
    for e in [".py", ".sh", ".yaml", ".yml", ".toml", ".bats"]:
        lines.append(f'    - ext: "{e}"\n')
    lines.append("exclude:\n  extensions:\n")
    for e in [".md", ".html", ".pdf", ".txt", ".png", ".jpg", ".jpeg",
              ".gif", ".svg", ".ico", ".zip", ".tar", ".gz", ".bz2"]:
        lines.append(f'    - ext: "{e}"\n')
    lines.append("  directories:\n")
    for d in [".git", ".ai", "pap", "docs", "__pycache__",
              ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules"]:
        lines.append(f'    - name: "{d}"\n')
    schema_path.write_text("".join(lines))


# ---------------------------------------------------------------------------
# _parse_schema_builtin
# ---------------------------------------------------------------------------

class TestParseSchemaBuiltin:
    _YAML = textwrap.dedent("""\
        schema_version: 1
        include:
          extensions:
            - ext: ".py"
              reason: Python
            - ext: ".sh"
              reason: Shell
        exclude:
          extensions:
            - ext: ".md"
              reason: Markdown docs
            - ext: ".html"
              reason: HTML
          directories:
            - name: ".git"
              reason: VCS metadata
            - name: "pap"
              reason: PAP docs
            - name: "chatgpt architecture"
              reason: Removed corpus
    """)

    def test_parses_include_exts(self):
        schema = _parse_schema_builtin(self._YAML)
        exts = [e["ext"] for e in schema["include"]["extensions"]]
        assert ".py" in exts and ".sh" in exts

    def test_parses_exclude_exts(self):
        schema = _parse_schema_builtin(self._YAML)
        exts = [e["ext"] for e in schema["exclude"]["extensions"]]
        assert ".md" in exts and ".html" in exts

    def test_parses_exclude_dirs(self):
        schema = _parse_schema_builtin(self._YAML)
        dirs = [d["name"] for d in schema["exclude"]["directories"]]
        assert ".git" in dirs and "pap" in dirs

    def test_handles_space_in_dir_name(self):
        schema = _parse_schema_builtin(self._YAML)
        dirs = [d["name"] for d in schema["exclude"]["directories"]]
        assert "chatgpt architecture" in dirs

    def test_empty_text_produces_empty_lists(self):
        schema = _parse_schema_builtin("schema_version: 1\n")
        assert schema["include"]["extensions"] == []
        assert schema["exclude"]["extensions"] == []
        assert schema["exclude"]["directories"] == []


# ---------------------------------------------------------------------------
# _rules_from_schema
# ---------------------------------------------------------------------------

class TestRulesFromSchema:
    def test_include_exts_lowercased(self):
        rules = _rules_from_schema(_MINIMAL_SCHEMA)
        assert ".py" in rules.include_exts
        assert ".YAML" not in rules.include_exts  # always lower

    def test_exclude_exts_present(self):
        rules = _rules_from_schema(_MINIMAL_SCHEMA)
        assert ".md" in rules.exclude_exts

    def test_exclude_dirs_present(self):
        rules = _rules_from_schema(_MINIMAL_SCHEMA)
        assert ".git" in rules.exclude_dirs
        assert "pap" in rules.exclude_dirs

    def test_empty_schema_produces_empty_rules(self):
        rules = _rules_from_schema({})
        assert len(rules.include_exts) == 0
        assert len(rules.exclude_exts) == 0
        assert len(rules.exclude_dirs) == 0


# ---------------------------------------------------------------------------
# _should_include
# ---------------------------------------------------------------------------

class TestShouldInclude:
    def test_python_file_included(self, tmp_path, rules):
        f = tmp_path / "foo.py"
        f.write_text("x = 1")
        assert _should_include(f, tmp_path, rules) is True

    def test_shell_file_included(self, tmp_path, rules):
        f = tmp_path / "foo.sh"
        f.write_text("#!/bin/bash")
        assert _should_include(f, tmp_path, rules) is True

    def test_yaml_included(self, tmp_path, rules):
        f = tmp_path / "config.yaml"
        f.write_text("key: value")
        assert _should_include(f, tmp_path, rules) is True

    def test_toml_included(self, tmp_path, rules):
        f = tmp_path / "pyproject.toml"
        f.write_text("[tool.ruff]")
        assert _should_include(f, tmp_path, rules) is True

    def test_bats_included(self, tmp_path, rules):
        f = tmp_path / "test_forge.bats"
        f.write_text("@test 'ok' { true; }")
        assert _should_include(f, tmp_path, rules) is True

    def test_markdown_excluded(self, tmp_path, rules):
        f = tmp_path / "ROADMAP.md"
        f.write_text("# Roadmap")
        assert _should_include(f, tmp_path, rules) is False

    def test_html_excluded(self, tmp_path, rules):
        f = tmp_path / "ROADMAP.html"
        f.write_text("<html></html>")
        assert _should_include(f, tmp_path, rules) is False

    def test_pdf_excluded(self, tmp_path, rules):
        f = tmp_path / "spec.pdf"
        f.write_bytes(b"%PDF-1.4")
        assert _should_include(f, tmp_path, rules) is False

    def test_git_dir_excluded(self, tmp_path, rules):
        d = tmp_path / ".git"
        d.mkdir()
        py = d / "hook.py"
        py.write_text("x=1")
        assert _should_include(py, tmp_path, rules) is False

    def test_hidden_dir_excluded(self, tmp_path, rules):
        d = tmp_path / ".somecache"
        d.mkdir()
        f = d / "data.py"
        f.write_text("x=1")
        assert _should_include(f, tmp_path, rules) is False

    def test_ai_dir_excluded(self, tmp_path, rules):
        d = tmp_path / ".ai"
        d.mkdir()
        f = d / "context.py"
        f.write_text("x=1")
        assert _should_include(f, tmp_path, rules) is False

    def test_pap_dir_excluded(self, tmp_path, rules):
        d = tmp_path / "pap"
        d.mkdir()
        f = d / "audit.py"
        f.write_text("x=1")
        assert _should_include(f, tmp_path, rules) is False

    def test_docs_dir_excluded(self, tmp_path, rules):
        d = tmp_path / "docs"
        d.mkdir()
        f = d / "helper.py"
        f.write_text("x=1")
        assert _should_include(f, tmp_path, rules) is False

    def test_nested_excluded_dir(self, tmp_path, rules):
        d = tmp_path / "pap" / "modules"
        d.mkdir(parents=True)
        f = d / "tool.py"
        f.write_text("x=1")
        assert _should_include(f, tmp_path, rules) is False

    def test_nested_included_file(self, tmp_path, rules):
        d = tmp_path / "proxmox-bootstrap"
        d.mkdir()
        f = d / "manager.py"
        f.write_text("x=1")
        assert _should_include(f, tmp_path, rules) is True

    def test_directory_not_included(self, tmp_path, rules):
        d = tmp_path / "mydir.py"
        d.mkdir()
        assert _should_include(d, tmp_path, rules) is False

    def test_unknown_extension_excluded(self, tmp_path, rules):
        f = tmp_path / "data.csv"
        f.write_text("a,b,c")
        assert _should_include(f, tmp_path, rules) is False

    def test_extension_check_case_insensitive(self, tmp_path, rules):
        f = tmp_path / "script.PY"
        f.write_text("x=1")
        assert _should_include(f, tmp_path, rules) is True


# ---------------------------------------------------------------------------
# compute_codebase_hash
# ---------------------------------------------------------------------------

class TestComputeCodebaseHash:
    def test_returns_eight_hex_chars(self, tmp_path, rules):
        (tmp_path / "foo.py").write_text("x=1")
        h = compute_codebase_hash(tmp_path, rules=rules)
        assert len(h) == 8
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self, t