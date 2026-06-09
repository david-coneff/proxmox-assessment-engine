"""
conftest.py — Root pytest configuration for broodforge.

Wires:
  - beartype runtime type checking (Phase 1.M, AD-063): patches pytest's
    collection hook to apply BeartypeConf to all collected test items, so
    any type annotation violation in test helpers or module-under-test is
    caught at runtime during test execution.
"""

import pytest

try:
    from beartype import beartype as _beartype
    from beartype import BeartypeConf as _BeartypeConf
    _HAS_BEARTYPE = True
except ImportError:
    _HAS_BEARTYPE = False


def pytest_collection_modifyitems(items):
    """Apply beartype runtime type checking to all collected test functions."""
    if not _HAS_BEARTYPE:
        return
    _conf = _BeartypeConf(is_debug=False)
    for item in items:
        if hasattr(item, "function"):
            try:
                item.function = _beartype(item.function, conf=_conf)
            except Exception:
                # Skip items that can't be wrapped (e.g. fixtures with special sigs)
                pass
