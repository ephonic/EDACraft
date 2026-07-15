#!/usr/bin/env python3
"""
Pre-commit physics check for TCAD.

Run automatically via git pre-commit hook, or manually:
    python scripts/pre_commit_check.py

Checks performed (fast — < 30 s total):
  1. C++ binding compiles without errors
  2. Physical-truth tests pass (div stencil, P bounds, carrier non-neg, etc.)
  3. Core regression tests pass

Exit code 0 = all checks passed; non-zero = do NOT commit.
"""

import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

CHECKS = []


def check(name):
    """Decorator to register a named check."""
    def deco(func):
        CHECKS.append((name, func))
        return func
    return deco


def run(cmd, cwd=None, timeout=300):
    """Run a command, return (returncode, stdout+stderr)."""
    try:
        r = subprocess.run(
            cmd, cwd=cwd or PROJECT_ROOT, capture_output=True,
            text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except Exception as e:
        return -2, str(e)


@check("1. Physical-truth tests (div stencil, P bounds, carriers)")
def test_physical_truths():
    """The fastest and most important check — catches core bugs."""
    rc, out = run([
        sys.executable, "-m", "pytest",
        "tests/test_physical_truths.py", "-v", "--tb=short", "-q"
    ], timeout=120)
    if rc != 0:
        return False, out[-2000:]
    return True, "All physical-truth tests passed"


@check("2. FE regression tests (Preisach, LK, switching, breakdown)")
def test_fe_regression():
    """Regression tests for ferroelectric + breakdown models."""
    rc, out = run([
        sys.executable, "-m", "pytest",
        "tests/test_preisach_model.py",
        "tests/test_fe_coupling_and_ionization.py",
        "tests/test_analytic_limits.py",
        "tests/test_dielectric_breakdown.py",
        "-q", "--tb=line"
    ], timeout=180)
    if rc != 0:
        return False, out[-2000:]
    return True, "FE regression tests passed"


@check("3. FE validation tests (NLS, traps, retention, endurance)")
def test_fe_validation():
    """New feature validation tests."""
    rc, out = run([
        sys.executable, "-m", "pytest",
        "tests/test_fe_validation.py",
        "tests/test_fefet_validation.py",
        "-q", "--tb=line"
    ], timeout=120)
    if rc != 0:
        return False, out[-2000:]
    return True, "FE validation tests passed"


def main():
    print(f"\n{BOLD}{'='*60}")
    print("  TCAD Pre-Commit Physics Check")
    print(f"{'='*60}{RESET}\n")

    all_passed = True
    total_time = 0

    for name, func in CHECKS:
        print(f"{BOLD}▶ {name}{RESET}")
        t0 = time.time()
        passed, detail = func()
        dt = time.time() - t0
        total_time += dt

        status = f"{GREEN}PASS" if passed else f"{RED}FAIL"
        print(f"  {status} ({dt:.1f}s){RESET}")
        if not passed:
            all_passed = False
            # Print last lines of output for debugging
            lines = detail.strip().split("\n")
            for line in lines[-15:]:
                print(f"  {RED}{line}{RESET}")
        print()

    print(f"{BOLD}{'='*60}")
    if all_passed:
        print(f"  {GREEN}ALL CHECKS PASSED ({total_time:.1f}s){RESET}")
        print(f"  {GREEN}Safe to commit.{RESET}")
    else:
        print(f"  {RED}SOME CHECKS FAILED ({total_time:.1f}s){RESET}")
        print(f"  {RED}DO NOT COMMIT until all checks pass.{RESET}")
        print(f"  {YELLOW}Fix the issues above, then re-run this script.{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
