# Complex report regression

The six design directories and `probes/` contain the exact RTL/TB/memory sources
from the user's 2026-10-25 complex REPORT fixtures. Do not weaken these checks by
editing those inputs. `extended/` adds independent boundary tests; the procedural
sampling stimulus explicitly avoids an unintended time-zero X-to-0 negedge.

```
python3 tests/complex_report/regression.py build/dsim /tmp/complex-report
```

The output directory retains generated C++, stdout/stderr and ordered VCD from
all backends and failed-prediction replays. `results.json` is marked PASS only
after the negative diagnostics and finite execution budget check also succeed.
CTest name: `rtl_complex_report`. Scope and limitations:
[complex-report-fixes.md](../../docs/complex-report-fixes.md).
