# Three-x-grid / two-time-step full-pulse matrix

Two new full 60 ps MoS2 pulses at x83/y9/z113 complete a **three-x-grid by
two-time-step** matrix with four sealed x69/x75 controls. Both new trajectories
pass the unchanged independent physical and linear acceptance checks. The refined x69/75/83
endpoint gates pass **54/54 at n128** and **54/54 at n256**.
These are local endpoint results, not global spatial convergence or joint
space/time qualification. Complete failures remain in JSON. The coarser x65/69/75 sequence is still
**52/54 at both dt**; its two bulk-potential failures are retained unchanged
from the [x75 study](../20261107-geometric-x75-time/README.md). The finer window
was declared in policy before launching x83, using the original x69/75/83
reference sequence, metrics, support, normalizations and limits. No coarse
result is retroactively qualified and no observable or threshold is dropped.

## Frozen protocol and physical checks

Both new drivers have identical bytes. A reversible AST check proves that only
the x selector changes from `x_m` to `x_m_endpoint3` in the accepted x65
GEOMETRIC_ND driver. CLI steps per phase is 128 or 256 (dt 0.15625 or 0.078125 ps).
Representative isothermal MoS2 parameters, y9/z113 geometry, traps, thermionic
contacts, cache release protocol and SI float128 native extension are unchanged.
All six matrix trajectories use the same frozen source/native identity and ND
ordering. Four full fields per pulse are saved at 0/20/40/60 ps.

Each case has a predeclared 6000 s wall/CPU budget, 4 GiB peak RSS and 48 GiB
address space. Cases run serially with one numerical thread. Nonlinear 1e-12,
original row-scaled true linear max-norm 1e-14, iteration and refresh gates are
unchanged.

| New control | Whole-run time (s) | Peak RSS (MiB) | Maximum nonlinear residual |
| --- | ---: | ---: | ---: |
| geometric_x83_n128 | 550.398 | 756.06 | 9.86552e-13 |
| geometric_x83_n256 | 1004.075 | 757.00 | 9.86215e-13 |

The [independent audit](independent_audit.json) adds
**1,997,422 physical and ledger checks** over 1152
new BE steps, two pulses and eight full fields. It reconstructs carrier
statistics and transport, traps, dielectric Poisson/flux and electrostatic
energy, contact charges and terminal currents. The x83 n128/n256 initial
states and initial linear diagnostics match bit for bit. Each new trajectory
rejects thirteen corruptions, including late-step ledger/residual faults,
wrong cadence, altered geometry and truncation.

Before launch, [auditor replay](auditor_tool_checks.json) reproduced exact
sealed x75 n128/n256 summaries and maxima, plus the original x83 MMD physics
result. Its synthetic ND-label fault replay earns no new physical credit.
The older x83 MMD trajectory has a different source inventory and is only a
replay fixture, not one of the six matrix corners or a same-source parity claim.

## Original spatial gates and signed interactions

The [spatial report](spatial_diagnostics.json) applies the exact original 54
endpoint metrics at each time resolution. The fixed 65x9x65 support,
normalizations, difference limit 0.01, increment-ratio limit 0.7 and analysis
cutoff 1e-8 are retained. Full common 69x9x113 field increments are reported
separately. [Diagnostic replay](diagnostic_tool_checks.json) reproduces the
sealed original x69/75/83 verdict exactly, plus inherited passing/failing
fixtures, signed-increment analytic checks and malformed-input rejection.

At n256, the two previously failing bulk-potential increments compare as
follows on the original fixed support. These are adjacent spatial increments,
not estimates or bounds of the absolute device solution error.

| Time (ps) | x69 to x75 increment (microV) | x75 to x83 increment (microV) | Original limit (microV) |
| --- | ---: | ---: | ---: |
| 20 | 284.247182 | 50.091286 | 250.0 |
| 60 | 252.016731 | 44.374161 | 250.0 |

The [interaction report](space_time_interaction.json) subtracts signed arrays
on exact nested 65x9x113 support before taking norms, for both adjacent x pairs:

`[u(x_fine,dt/2)-u(x_coarse,dt/2)] - [u(x_fine,dt)-u(x_coarse,dt)]`.

It reports 40 field/phase/pair metrics, including initial states. The maximum
normalized mixed increment is **5.84335892e-07**; **18/40** exceed the
inherited **1e-08** normalized analysis floor. The first x69/75 pair exactly
reproduces the second pair in the [x75 study](../20261107-geometric-x75-time/README.md).
This classifies resolution only; no new acceptance threshold, physical
decoupling claim or error bound is introduced.

| Time (ps) | x69 to x75 mixed bulk potential (V) | x75 to x83 mixed bulk potential (V) |
| --- | ---: | ---: |
| 20 | 9.85187017e-09 | 2.73661056e-09 |
| 40 | 1.46083973e-08 | 4.05829448e-09 |
| 60 | 1.00452498e-08 | 2.79015987e-09 |

The [time trace report](time_trace_diagnostics.json) retains the original
interval-matched comparator for ending-time states, BE interval currents and
signed cumulative terminal charges, including gate edges. Both inherited
x69/x75 comparisons reproduce the previous results exactly. The two time
resolutions on x83 provide increments, not a temporal order estimate.

## Scope and next controls

This study adds only the two x83 pulses: 1152 steps and eight fields. The four
x69/x75 matrix pulses are inherited once. All owned workers exited. Solver
and trace tests (245 and 25) are inherited by unchanged hashes, with zero
reruns. No solver source was changed. Native, production, calibration and
the protected 1078-file original inventory remain unchanged. No release was
published.

The nested x grids add nodes locally near contacts; their node counts do not
define a uniform global refinement ratio. Passing increment-ratio gates does
not establish a spatial Richardson order or asymptotic error bound. Matched
z/time controls, additional temporal resolution and an explicit observable
error budget remain necessary for broader numerical qualification. General
2D logic/memory/material qualification, quantum transport and complete
Sentaurus equivalence remain open.

See [matrix scope](matrix_audit.json), [frozen policy](policy.json),
[provenance](PROVENANCE.json), [reproduction](reproduction/README.md) and
[hashes](MANIFEST.json).
