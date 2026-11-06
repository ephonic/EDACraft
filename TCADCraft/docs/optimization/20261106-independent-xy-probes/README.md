# Third x probe and independent y sensitivity

The consecutive x69/x75/x83 sequence passes **26 / 26**
initial/first-BE local metrics under the original acceptance gates. A new y17
probe supplies the first independent y increment in this follow-up series.
Both new probes complete and pass independent physical audits, but **the cohort
fails its frozen resource budget**: y17 exceeds 6 GiB peak RSS. There are
**zero new complete pulses**. The [prior full endpoint-z study](../20261106-endpoint-full/README.md)
and its failed x65/x69/x75 short-probe evidence remain preserved.

## Controlled execution and independent audit

| New probe | Grid | Seconds | Peak process RSS (MiB) |
| --- | --- | ---: | ---: |
| endpoint_x3_probe | 83 x 9 x 113 | 208.97 | 2462.29 |
| independent_y1_probe | 65 x 17 x 113 | 668.01 | 6311.34 |

Each probe saves its initial state and one BE step at dt 0.15625 ps: two new
dynamic steps, four new field checkpoints. The same representative isothermal
MoS2/trap/contact parameters, SI float128 native extension and optional MMD
ordering are used. Numerical solver source is unchanged; no native rebuild,
release or deployment occurred. Nonlinear tolerance remains `1e-12`; accepted
true row-scaled linear residual max norm remains at most `1e-14`.

**1,241,810 new independent physical/ledger checks pass.**
The sealed physical checker is byte-identical to the previous version. Its
frozen geometry selector now reads an explicit y key as well as x/z keys.
Each probe's six deliberately corrupted variants are rejected (charge ledger,
dt, linear residual, bulk field, gate drive and geometry). The geometry fault
uses x for the x probe and y for the y probe. A separate inherited-data replay
checks the unchanged physical checker and receives zero new simulation credit.

Cases ran serially with one BLAS/OpenMP thread. Frozen budgets were 900 s for x,
1,800 s for y, 16 GiB address space and 6 GiB peak RSS per case. The worker
rejects y17 after numerical export because its peak RSS exceeds the frozen
limit. The unchanged frozen acceptance auditor also rejects the cohort.
A separate supplementary auditor verifies the completed fields without
relaxing or overriding that resource failure. Every accepted linear record,
atomic checkpoint and final export agrees. All owned workers exited;
numerical/native identities and production target/files were reverified.

## Consecutive x refinement

The inherited x69/x75 meshes and new x83 mesh keep y9/z113. Eight new midpoints
bisect x75 cells in 0.125 nm source/drain neighborhoods; all inherited nodes and
physical contact bounds remain exact. Minimum x spacing is 0.0150568 nm. This
is a continuum discretization check near an ideal contact edge, not atomistic
resolution or a material-accuracy claim.

All original metrics use fixed **65 x 9 x 65** common nodes, unchanged scales,
normalized difference limit `0.01`, increment-ratio limit `0.7` and roundoff
floor `1e-8`. The bulk-potential difference gate is 0.25 mV. These localized
increments do not define an observed uniform-grid convergence order.

| Time (ps) | x69 to x75 bulk change (mV) | x75 to x83 (mV) | Increment ratio |
| --- | ---: | ---: | ---: |
| 0 | 0.235125 | 0.0413845 | 0.176011 |
| 0.15625 | 0.29445 | 0.0518042 | 0.175935 |

Remaining x metrics:

- None under the original local probe gates.

This finer consecutive sequence supplies additional short-probe evidence.
It preserves the older x65/x69/x75 first-step failure rather than changing its
threshold or data. It does not establish 20/40/60 ps x acceptance.

## Independent y increment

The y9/y17 pair keeps x65/z113 and bisects every y interval, preserving all
old coordinates. Minimum y spacing is 6.25 nm. The y9 initial/first-BE reference
is inherited from the sealed SI probe pipeline; its ordering predates optional
MMD, while physical parameters and native profile match. It is not a new solve.
Available ordering-parity data are reported separately: this y9 reference and
the inherited MMD full pulse differ initially by at most
`4.00374e-15 V`
in the bulk field and by
`3.84553e-19 A`
in first-BE total terminal currents. First-BE full-field ordering parity is
unavailable and is not claimed.

| Time (ps) | Bulk-potential change (mV) | Sheet-potential change (microV) | Max total terminal-current change (nA) |
| --- | ---: | ---: | ---: |
| 0 | 0.000205849 | 0.116415 | n/a (initial) |
| 0.15625 | 0.00020731 | 0.121002 | 1.98577e-05 |

Only one independent y increment is available. There is **no y convergence
ratio, y-order estimate or y acceptance claim**. The
[diagnostics](xy_diagnostics.json) include all original normalized observables
and maximum-change locations. Additional field differences cover every node
of the shared coarsest meshes (x69/y9/z113 and x65/y9/z113); these are descriptive
checks, not newly introduced acceptance gates. No interpolation is used.
On the full shared x69/y9/z113 support, the x75-to-x83 bulk-field changes are
0.118684 mV initially and
0.148604 mV after the first BE step.

## Reproduction and outstanding scope

[Exact drivers and coordinates](reproduction/README.md), [frozen policy](policy.json),
[physical audit](independent_audit.json), [checker replay](auditor_tool_checks.json),
[source/archive identities](PROVENANCE.json) and [file hashes](MANIFEST.json)
accompany this report. Raw fields and accepted-step journals remain in the
local archive identified by provenance.

The 215 solver tests and 25 postprocessing tests are inherited and were not
rerun. Reducing y-grid memory use, complete-pulse x/y studies, further independent y refinement and joint
spatial/time qualification remain open. This evidence does not establish
general 2D logic/memory support, material calibration, quantum transport,
general energy/entropy closure or full Sentaurus equivalence.
