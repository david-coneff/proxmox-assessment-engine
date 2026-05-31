"""Tests for the parser module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.parser import parse_raw_audit, register_parser, _deep_merge


def test_deep_merge_simple():
    base = {"a": 1}
    _deep_merge(base, {"b": 2})
    assert base == {"a": 1, "b": 2}


def test_deep_merge_nested():
    base = {"hardware": {"cpu": {"model": "old"}}}
    _deep_merge(base, {"hardware": {"cpu": {"model": "new"}, "memory": {}}})
    assert base["hardware"]["cpu"]["model"] == "new"
    assert "memory" in base["hardware"]


def test_deep_merge_override_non_dict():
    base = {"x": [1, 2]}
    _deep_merge(base, {"x": [3]})
    assert base["x"] == [3]


def test_audit_base_keys():
    r = parse_raw_audit({})
    assert r["schema_version"] == "1.0"
    assert "timestamp" in r
    assert "hostname" in r


def test_audit_skips_errors():
    r = parse_raw_audit({"hardware": {"error": "dmidecode not found"}})
    assert "hardware" not in r


def test_audit_uses_registered_parser():
    @register_parser("_dummy_test")
    def p(data):
        return {"os": {"name": data["name"]}}

    r = parse_raw_audit({"_dummy_test": {"name": "TestOS"}})
    assert r["os"]["name"] == "TestOS"

    from engine import parser as pm
    del pm._PARSERS["_dummy_test"]
