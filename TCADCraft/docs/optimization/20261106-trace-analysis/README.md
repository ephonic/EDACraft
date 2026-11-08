# Three-resolution trace analysis with less memory

`benchmarks/sheet_refinement_trace.py` now measures observed temporal orders from
three same-mesh backward-Euler trajectories. Both increments use the same coarse
ending times and physical intervals. Fine total currents are averaged over each
coarse interval, preserving gate-edge impulses. Ending-time conduction currents
and signed cumulative charge integrals are reported separately.

```bash
python benchmarks/sheet_refinement_trace.py COARSE_STEM FINE_STEM \
  --middle MIDDLE_STEM --output three_time_trace.json
```

Each stem identifies a JSON/NPZ export pair. Phase durations, physical
configuration, complete phase inventories, uniform dt and equal initial states
are checked. Adjacent resolution ratios must match. Each adjacent pair retains
the original `1e-24 s` accumulated-time gate. The separately reported three-way
clock spread can be larger because adjacent floating-point errors add; matching
uses prescribed uniform-step indices. Observed order is unresolved below the
normalized `1e-8` roundoff floor. No device qualification or asymptotic error
bound is inferred.

The original two-stem invocation remains available without `--middle`.
`compare_traces` is AST-identical to its prior implementation. The CLI's new
trace-only loader skips dynamic full-field result/previous arrays, while
retaining complete initial states and every checkpoint's configuration/drive.
The default `load_record` behavior still loads all fields.

Twenty-five [postprocessing tests](trace_analysis_tests.json) pass, including
eleven new cases for known first/second order, impulses, shared observation
support, accumulated-clock roundoff, invalid configurations and trace-only
loading parity. These tests import no TCAD solver/native extension.

An [isolated-process measurement](trace_loading_benchmark.json) on two inherited
complete 60 ps records found:

| Measurement | Full loading | Trace-only loading |
| --- | ---: | ---: |
| Retained NumPy arrays (MiB) | 57.70 | 10.59 |
| Peak traced allocations (MiB) | 62.16 | 14.85 |
| Measured seconds | 0.856 | 0.504 |

Retained arrays decreased by **81.65%**, with identical canonical comparison JSON
hashes. Traced allocations are not process RSS. There was one timing measurement
per mode; this does not establish a statistical speedup. These inherited records
are not new simulations, and this change does not accelerate the PDE solver.

The separate third-time-step pulse and contact endpoint probes are still being
computed when this feature is committed; they are not accepted by this report.
Source identities and file hashes are included in [provenance](PROVENANCE.json)
and [manifest](MANIFEST.json). Numerical solver sources, release artifacts and
production deployment are unchanged.
