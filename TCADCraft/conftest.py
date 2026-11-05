"""Keep operational scripts and sealed validation copies out of pytest.

Run archived validation drivers explicitly with Python. They are executable
evidence, and importing them during test collection can change sealed files.
"""
from pathlib import Path

import pytest


_ROOT = Path(__file__).resolve().parent
_TESTS = _ROOT / "tests"


def _test_path(path):
    resolved = Path(path).resolve()
    return resolved == _TESTS or _TESTS in resolved.parents


def pytest_sessionstart(session):
    # An explicit pytest file argument can bypass normal recursion exclusions.
    # Reject it before importing test modules, including node-id selections.
    invocation_dir = Path(session.config.invocation_params.dir)
    for argument in session.config.args:
        path = (invocation_dir / str(argument).split("::", 1)[0]).resolve()
        if path != _ROOT and not _test_path(path):
            raise pytest.UsageError(
                "TCAD pytest collection is restricted to tests/: "
                f"{argument}. Run validation drivers explicitly with Python."
            )


def pytest_ignore_collect(collection_path, config):
    path = Path(collection_path).resolve()
    if path == _ROOT or _test_path(path):
        return None
    return True
