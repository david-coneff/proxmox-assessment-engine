"""Schema validation utilities."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

_SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"
_SCHEMA_PATH = _SCHEMAS_DIR / "assessment.schema.json"
_schema: dict | None = None
_registry: Registry | None = None

_BASE_ID = "https://github.com/broodforge/schemas/"


def _load_schema() -> tuple[dict, Registry]:
    global _schema, _registry
    if _schema is None:
        _schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8-sig"))
        resources: list[tuple[str, Resource]] = []
        for schema_file in _SCHEMAS_DIR.glob("*.json"):
            sub = json.loads(schema_file.read_text(encoding="utf-8-sig"))
            resource = Resource.from_contents(sub, default_specification=DRAFT7)
            # Register under file URI, bare filename, and GitHub base URL
            resources.append((schema_file.as_uri(), resource))
            resources.append((schema_file.name, resource))
            resources.append((_BASE_ID + schema_file.name, resource))
            if "$id" in sub:
                resources.append((sub["$id"], resource))
        _registry = Registry().with_resources(resources)
    return _schema, _registry


def validate_assessment(data: dict) -> list[str]:
    """Return a list of validation error messages, empty if valid."""
    schema, registry = _load_schema()
    validator = jsonschema.Draft7Validator(schema, registry=registry)
    return [err.message for err in validator.iter_errors(data)]
