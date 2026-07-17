"""Shared pytest configuration for the tcad test suite.

Registers the ``slow`` marker used by solver-backed integration tests
(``tests/test_evolution.py``).  Those tests are skipped unless the caller opts
in via ``TCAD_RUN_SLOW=1``; the marker makes them selectable with
``-m slow`` / excludable with ``-m "not slow"``.
"""

import os


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: solver-backed integration tests (set TCAD_RUN_SLOW=1 to run)",
    )
