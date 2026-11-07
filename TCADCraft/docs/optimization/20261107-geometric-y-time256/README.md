# Three-y-grid / two-time-step full-pulse matrix

Two fresh x65/z113 MoS2 pulses on y9 and y17 complete a **three-y-grid by
two-time-step** matrix together with four sealed controls. Each new pulse
contains 768 BE steps / 60 ps and full fields at 0/20/40/60 ps.
The original half-dt y endpoint test passes **54/54** metrics.
This is a local y endpoint result at a second dt. It establishes no global
spatial convergence, asymptotic error bound or joint space/time qualification.

## Frozen protocol and physical checks

Both driver files are byte-identical to their accepted n128 full controls;
only CLI steps per phase changes 128 to 256 (dt 0.15625 to 0.078125 ps).
Geometry, representative isothermal MoS2 parameters, traps, thermionic contacts,
GEOMETRIC_ND ordering and SI float128 native extension are unchanged. Each run
clears the initial linear cache explicitly before stepping.

The predeclared per-case budget is 9,000 s wall/CPU, 8 GiB peak process RSS,
48 GiB address space. Cases run serially with one numerical thread. The
nonlinear `1e-12`, original row-scaled true linear max-norm `1e-14`, iteration
limits and refresh policy are unchanged.

| New control | Whole-run time (s) | Peak RSS (MiB) | Maximum nonlinear residual |
| --- | ---: | ---: | ---: |
| geometric_y9_n256 | 906.306 | 604.82 | 9.88426e-13 |
| geometric_y17_n256 | 2013.681 | 1829.23 | 9.7513e-13 |

The [independent audit](independent_audit.json) adds
**2,286,174 physical and ledger checks** over two
complete pulses, all 1,536 steps, eight full fields and 1,538 linear diagnostics.
It reconstructs sheet statistics/transport, traps, dielectric Poisson and flux,
electrostatic energy, contact charges and terminal currents. Both initial full
states, scalar states and linear diagnostics match their same-mesh n128 parent
bit for bit. Different dt values do not imply first-BE parity.

Before launch, [auditor replay](auditor_tool_checks.json) reproduces the exact
sealed y9/y17 n128 and y33 n256 summaries and maxima. The physical oracle and
cadence guard bytes match the accepted third-time study. Thirteen corruptions
are rejected on the n256 replay and independently on each new trajectory,
including late-step charge/residual corruption, wrong cadence and truncation.
Replay and fault injection earn zero new physical credit.

## Spatial verdict and signed interaction

The [original spatial test](spatial_diagnostics.json) retains all 54 observables,
normalizations, `0.01` difference limit, `0.7` increment-ratio limit and `1e-8`
roundoff cutoff on fixed 65x9x65 support. It separately reports full common
65x9x113 field increments. [Tool checks](diagnostic_tool_checks.json) reproduce
sealed passing and failing fixtures and the previous n128 y verdict exactly.
Failed metrics, if any, remain in the JSON report and are not waived.

The [interaction report](space_time_interaction.json) subtracts **signed field
arrays before taking norms**:

`[u(y_fine,dt_fine)-u(y_coarse,dt_fine)] - [u(y_fine,dt_coarse)-u(y_coarse,dt_coarse)]`.

All 40 field/phase/pair metrics use nested common 65x9x113 support. This measures
how a spatial increment changes when dt halves; subtracting two max-norm
magnitudes would lose cancellation and location information. Analytic interaction,
additive cancellation and constant-field checks, plus shape/finite/scale/clock/
nested-support fault rejection, validate the analysis helper. No interaction
threshold or error-bound assumption is added.

| Time (ps) | y9 to y17 mixed bulk-potential increment (microV) | y17 to y33 mixed increment (microV) |
| --- | ---: | ---: |
| 20 | 1.483047e-05 | 4.935344e-06 |
| 40 | 2.890074e-05 | 9.469564e-06 |
| 60 | 1.625881e-05 | 5.621628e-06 |

[Interval-matched traces](time_trace_diagnostics.json) compare the two time
resolutions on every y grid with the unchanged comparator. Scalar states use
common ending times; BE currents use matching coarse physical intervals,
including gate-edge impulses and signed cumulative charges. The y33 result
exactly reproduces the sealed [half-dt study](../20261107-geometric-time256/README.md).
Two time resolutions on y9/y17 provide increments rather than temporal orders.

## Scope and reproduction

Four matrix pulses are inherited and counted once: y9/y17/y33 at n128 plus y33
at n256. This study adds two pulses, 1,536 steps and eight fields. The separate
y33 n512 [study](../20261107-geometric-time512/README.md) provides three-time
orders on that mesh; it is not a seventh pulse in this six-run matrix.
The 245 solver and 25 trace tests are inherited by unchanged source hashes,
with zero reruns. All owned workers exited; native, production, calibration
and 1,078 protected original-source files are unchanged. No release was published.

Next evaluate temporal resolution on the other meshes and coupled x/z/y/time
refinement against an explicit error budget. General 2D logic/memory/material
qualification, quantum transport and complete Sentaurus equivalence remain open.
See [matrix scope](matrix_audit.json), [policy](policy.json), [replay](reproduction/README.md),
[provenance](PROVENANCE.json) and [hashes](MANIFEST.json).
