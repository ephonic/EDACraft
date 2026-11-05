"""Exercise collection in disposable trees; never import archived drivers."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

import pytest


SOURCE = Path(__file__).resolve().parents[1]


@pytest.fixture
def guarded_tree(tmp_path):
    root = tmp_path / "repository"
    root.mkdir()
    for name in ("pytest.ini", "conftest.py"):
        shutil.copy2(SOURCE / name, root / name)
    tests = root / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("", encoding="utf-8")
    (tests / "fixture_value.py").write_text("VALUE = 37\n", encoding="utf-8")
    (tests / "test_live.py").write_text(
        "from fixture_value import VALUE\ndef test_live():\n    assert VALUE == 37\n", encoding="utf-8")
    archive = root / "docs" / "validation" / "old_run"
    archive.mkdir(parents=True)
    sentinel = root / "IMPORTED_OPERATIONAL_SCRIPT"
    dangerous = (
        "from pathlib import Path\n"
        f"Path({str(sentinel)!r}).write_text('changed')\n"
        "raise AssertionError('operational script was imported')\n"
    )
    for name in ("repair_test.py", "test_archived.py"):
        (archive / name).write_text(dangerous, encoding="utf-8")
    (root / "repair_test.py").write_text(dangerous, encoding="utf-8")
    return root, sentinel


def invoke(tree, args, *, cwd=None):
    root, sentinel = tree
    # A nested pytest must not inherit plugins or parent command-line options.
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    for name in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTEST_CURRENT_TEST"):
        env.pop(name, None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *args],
        cwd=cwd or root, env=env, text=True, capture_output=True, timeout=30,
    )
    assert not sentinel.exists(), result.stdout + result.stderr
    return result


@pytest.mark.parametrize("selection", [[], ["."], ["tests"], ["tests/test_live.py"],
                                    ["tests/test_live.py::test_live"]])
@pytest.mark.parametrize("collect_only", [False, True])
def test_default_and_broad_collection_do_not_import_operations(guarded_tree, selection, collect_only):
    result = invoke(guarded_tree, [*selection, *(["--collect-only"] if collect_only else [])])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 test collected" in result.stdout if collect_only else "1 passed" in result.stdout


@pytest.mark.parametrize("selection", [
    "docs", "docs/validation", "docs/validation/old_run",
    "docs/validation/old_run/repair_test.py",
    "docs/validation/old_run/test_archived.py::test_anything",
    "repair_test.py", "tests/../docs/validation/old_run/repair_test.py",
])
def test_explicit_operational_selection_is_rejected_before_import(guarded_tree, selection):
    result = invoke(guarded_tree, ["--collect-only", selection])
    assert result.returncode == 4, result.stdout + result.stderr
    assert "restricted to tests/" in result.stderr


def test_absolute_archived_selection_rejected(guarded_tree):
    root, _ = guarded_tree
    result = invoke(guarded_tree, [str(root / "docs/validation/old_run/repair_test.py")])
    assert result.returncode == 4 and "restricted to tests/" in result.stderr


def test_invocation_inside_tests_keeps_live_tests(guarded_tree):
    root, _ = guarded_tree
    result = invoke(guarded_tree, [], cwd=root / "tests")
    assert result.returncode == 0 and "1 passed" in result.stdout


@pytest.mark.parametrize("explicit", [False, True])
def test_symlink_inside_tests_cannot_import_archived_scripts(guarded_tree, explicit):
    root, _ = guarded_tree
    alias = root / "tests" / "test_alias.py"
    try:
        alias.symlink_to(root / "docs/validation/old_run/repair_test.py")
    except OSError:
        pytest.skip("symlink creation unavailable on this host")
    result = invoke(guarded_tree, ["tests/test_alias.py"] if explicit else ["."])
    assert result.returncode == (4 if explicit else 0), result.stdout + result.stderr
    if not explicit:
        assert "1 passed" in result.stdout
