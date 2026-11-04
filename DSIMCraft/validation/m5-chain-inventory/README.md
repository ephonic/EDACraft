# Potential combination link inventory

Read-only analysis of the current whole generated real and feedback programs.
Static compact net counts, watchers and full degree histograms exactly match the
independently instrumented actual runtime census in `m5-topology-profile`.

The real design has 130,072 potential single-watch links between single-output
nonconstant combinational cells. Only **166** enter unary cells; 59,517 enter
two-input and 69,774 three-input cells, with 615 remaining links. The feedback
case has **zero** such links. A simple unary-chain strategy therefore has very
limited static coverage here. These counts are not activity or speed estimates.

Boundary exclusions: sequential cells, multiple outputs, noncompact outputs,
multiple drivers, repeated watchers and the conservative Kahn residual. All real
combinational cells pass the Kahn sweep in this graph, which does not prove that
arbitrary execution fusion preserves event ordering. External inputs to a
multi-input target can already have pending work. FIFO position, fixed rearm,
initialization and instruction limits must be preserved before claiming safety.

`chains.py` handles the specific generated-code schema including sentinels and
atomic structural copies; unknown schemas fail. `verify.py` recomputes counts
and checks the measured census. No generated code or production source changes.
