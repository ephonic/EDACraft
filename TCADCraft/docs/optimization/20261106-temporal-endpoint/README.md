# Third temporal resolution and contact-endpoint probes

One new complete 60 ps MoS2 pulse and three initial/first-BE spatial probes
passed independent physical audits. The third temporal resolution enables
observed-order measurements on a fixed mesh. The spatial probes test where
further endpoint refinement is useful; they do not close the four retained
full-pulse bulk-potential failures from the [previous study](../20261106-contact-z-time/README.md).

## Execution and physical audit

All cases ran serially, with one BLAS/OpenMP thread, the same frozen numerical
source and SI float128 native extension, representative homogeneous isothermal
MoS2/trap/contact parameters, and optional MMD Newton-preconditioner ordering.
Nonlinear tolerance remains `1e-12`; accepted true row-scaled linear residual
max norm remains at most `1e-14`. No numerical solver source changed.

| New case | Grid | Mode | Dynamic steps | Seconds | Peak process RSS (MiB) |
| --- | --- | --- | ---: | ---: | ---: |
| local_z1_n512 | 65 x 9 x 81 | full | 1536 | 2429.99 | 695.95 |
| endpoint_z1_probe | 65 x 9 x 121 | probe | 1 | 161.79 | 2048.13 |
| endpoint_z2_probe | 65 x 9 x 129 | probe | 1 | 179.45 | 2382.22 |
| endpoint_x1_probe | 69 x 9 x 113 | probe | 1 | 140.79 | 1943.68 |

The new full pulse uses 512 steps per 20 ps phase, for **1,536 new full-pulse
steps**. Three probes add **three first-BE steps**, each at the original dt.
There are ten new full-field checkpoints: four in the pulse and two per probe.
Full fields are not audited at every dynamic step.

An earlier attempt was stopped after 176 logged partial steps because measured
CPU allocation/throughput predicted exceeding its frozen 2,400 s wall budget.
Its [partial evidence was preserved](aborted_attempt.json) and receives zero
complete-pulse credit. This separately frozen retry uses byte-identical drivers
and the unchanged physical auditor, with 4,800 s for the pulse and 900 s per
probe. No physical tolerance was relaxed.

**1,847,584 new independent physical/ledger checks**
pass, reconstructing finite-volume bulk/sheet equations, carrier statistics,
trap kinetics, terminal charges and current/charge balance. All accepted linear
records and atomic phase exports match the final results. Six corruptions are
rejected, including an interior fine-time ledger, dt, linear residual, bulk
field, gate drive and probe geometry. All owned workers exited; source/native
identities and the production target/files were reverified.

## Temporal observations on one fixed mesh

The fixed grid is **65 x 9 x 81**. The 128- and 256-step controls are inherited;
only the 512-step pulse is new. The three dt values are 0.15625, 0.078125 and
0.0390625 ps. Initial physical states are identical. Field norms below use the
same complete saved mesh at 20/40/60 ps.

| Time (ps) | Bulk potential change, 128 to 256 (microV) | 256 to 512 (microV) | Observed order |
| --- | ---: | ---: | ---: |
| 20 | 6.23399 | 3.09055 | 1.01230 |
| 40 | 10.3153 | 5.10947 | 1.01354 |
| 60 | 6.62324 | 3.28942 | 1.00970 |

The [field report](three_time_fields.json) also covers sheet phi, Fn, Fp and trap
occupancy. Observed order is `log2(norm(delta_128_256)/norm(delta_256_512))`;
increments below the inherited normalized roundoff floor `1e-8` are unresolved.
Three time resolutions measure an observed order; they do not prove an asymptotic
regime, an analytic error bound, or general time-step independence.

## Entire current traces on identical intervals

The extended NumPy-only `benchmarks/sheet_refinement_trace.py --middle ...`
evaluates both increments at the same **384 coarse ending times**, rather than
taking maxima on different time supports. BE currents/rates are averaged over
the same coarse physical intervals; common-ending-time conduction and signed
cumulative charge integrals are also reported. Gate-edge impulses stay in their
correct intervals.

| Terminal total current | 128 to 256 max interval change (A) | 256 to 512 max interval change (A) | Observed order |
| --- | ---: | ---: | ---: |
| total/source | 1.55803e-08 | 7.86215e-09 | 0.98673 |
| total/drain | 1.59479e-08 | 8.06466e-09 | 0.98368 |
| total/top_gate | 1.57641e-08 | 7.9634e-09 | 0.98519 |
| total/bottom_gate | 1.57641e-08 | 7.9634e-09 | 0.98519 |

See [all trace quantities and error locations](three_time_trace.json). Each
adjacent resolution pair passes the unchanged `1e-24 s` accumulated-clock gate.
The maximum three-way accumulated-clock spread is
`1.37648024e-24 s`; values are matched by
their prescribed uniform-step indices. The spread is reported separately;
no adjacent time gate or physical acceptance threshold was relaxed.

Twenty-five postprocessing tests pass, including eleven new tests for known
first/second order, impulses, fixed observation support, accumulated-clock
roundoff and invalid initial states/ratios. The original two-trace comparison
function is AST-identical to its prior version. The 215 solver tests are
inherited and were not rerun.

## Less memory for trace postprocessing

The CLI now skips loading dynamic full-field results/previous states that its
trace comparisons do not use. It still loads complete initial states and every
checkpoint's physical configuration/drive, preserving those checks. Full-field
callers keep the original default `load_record` behavior.

An [isolated-process measurement](trace_loading_benchmark.json) on two inherited
complete pulse records retained 57.70 MiB of NumPy arrays with full loading and
10.59 MiB with trace-only loading, an 81.65% reduction. Comparison results have
identical canonical JSON hashes. Peak traced allocations were 62.16 and
14.85 MiB; these are Python/NumPy traced allocations, not process RSS. There
was one timing measurement per mode, so no statistical speedup is claimed.
This postprocessing change does not accelerate the numerical solver itself.

## Narrow endpoint refinement

The parent local-z2 mesh has 113 z nodes. Two narrower bisections add eight
nodes each, yielding 121 and 129 z nodes. Their neighborhoods shrink to 0.15625
and 0.078125 nm about each contact endpoint, preserving inherited nodes and
exact `z = +/-2.5 nm` bounds. An independent x probe bisects four cells within
0.5 nm of the source/drain planes, giving 69 x nodes with the parent 113 z nodes.
Minimum z spacings are 0.0390625 and 0.01953125 nm, used here to study the
continuum discretization around the ideal contact endpoint.
No terminal charge or contact flux rescaling is applied.

The reference is an inherited, sealed SI initial/first-BE local-z2 probe. Its
ordering predates optional MMD; its physical parameters/native profile match.
It is not counted again as a new solve. All spatial increments below use fixed
original **65 x 9 x 65** common nodes, not changing sample locations.

| Time (ps) | Parent to endpoint-z1 bulk change (mV) | Endpoint-z1 to z2 (mV) | z increment ratio | Independent x change (mV) |
| --- | ---: | ---: | ---: | ---: |
| 0 | 0.220038 | 0.0520485 | 0.236544 | 0.748746 |
| 0.15625 | 0.275456 | 0.0651613 | 0.236558 | 0.937946 |

The inherited local diagnostic scales and limits (`0.01`, `0.7`, roundoff
`1e-8`) are retained. **26 / 26 initial/first-BE z metrics pass**.
Remaining probe metrics:

- None in this initial/first-step local diagnostic.

See [spatial diagnostics and maximum-change locations](endpoint_spatial_diagnostics.json).
The single independent x increment is a sensitivity measurement, not an x
convergence ratio. These short probes do not replace 20/40/60 ps spatial fields
or the original independent-axis and joint global spatial studies. The earlier
four complete-pulse bulk-potential failures remain open.

## Reproduction and scope

[Exact drivers and mesh coordinates](reproduction/README.md), [frozen policy](policy.json),
[independent audit](independent_audit.json), [resource records](resources.json),
[source/archive identities](PROVENANCE.json), [tool tests](trace_analysis_tests.json)
and [file hashes](MANIFEST.json) accompany this report. Raw fields and accepted
step journals remain in the local archive identified by provenance.

This is numerical development evidence. Material calibration, general 2D
logic/memory qualification, quantum transport, general energy/entropy closure
and full Sentaurus equivalence are not established. Tagged release and
production deployment are unchanged.
