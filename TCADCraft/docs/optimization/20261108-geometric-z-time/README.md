# Three-z-grid / two-time-step full-pulse matrix

Four new full 60 ps MoS2 pulses at x83/y9, with z121 and z129 at n128 and
n256, complete a six-corner matrix with two sealed z113 controls from the
[x83 study](../20261107-geometric-x83-time/README.md). All four new
trajectories pass the unchanged independent physical and linear checks.
The original 54 spatial endpoint gates **pass**: **54/54 at
n128** and **54/54 at n256**. Full failures, if any, remain in
[spatial diagnostics](spatial_diagnostics.json). These results establish no
global spatial convergence or joint space/time qualification.

## Frozen protocol and independent checks

A reversible AST check proves that each new driver differs from the sealed
x83/y9/z113 driver only in its z selector: `z_m_level2` becomes
`z_m_endpoint1` or `z_m_endpoint2`. Driver bytes on each z mesh are identical
across time steps. Each pulse has three 20 ps phases with 128 or 256 BE steps
per phase (dt 0.15625 or 0.078125 ps), saving full fields at 0/20/40/60 ps.
Representative isothermal MoS2 parameters, traps, thermionic contacts,
GEOMETRIC_ND ordering and the cache-release protocol remain identical.

All six corners have the same 291-source-file, seven-test-source-file and
SI float128 native identity. Before launch, the physical auditor reproduced
the sealed z113 n128/n256 summaries and maxima exactly. Diagnostic replay
reproduced the original MMD z113/121/129 **54/54** result on its original
x65/y9 geometry, together with inherited passing and failing fixtures.
That older source inventory is a replay fixture, not a corner in this matrix.
Replays and analytic/fault checks earn zero new simulation credit.

Each case ran serially with one numerical thread under frozen 6000 s
wall/CPU, 4 GiB peak RSS and 48 GiB address-space caps. The original nonlinear
1e-12 and row-scaled true-linear max-norm 1e-14 limits remain unchanged.

| New control | Whole-run time (s) | Peak RSS (MiB) | Maximum nonlinear residual |
| --- | ---: | ---: | ---: |
| geometric_z121_n128 | 649.132 | 889.09 | 9.85606e-13 |
| geometric_z121_n256 | 1187.356 | 888.28 | 9.85188e-13 |
| geometric_z129_n128 | 803.783 | 994.96 | 9.84719e-13 |
| geometric_z129_n256 | 1318.556 | 996.85 | 9.84783e-13 |

The [independent audit](independent_audit.json) adds
**4,407,452 physical and ledger checks** over
**2304 new BE steps, four full pulses and sixteen full-field checkpoints**.
It reconstructs carrier statistics and transport, traps, dielectric
Poisson/flux and electrostatic energy, contact charges and terminal currents.
Each mesh's n128/n256 initial fields and linear diagnostics match bit for bit.
All four trajectories reject thirteen corruptions, including late-step
ledger/residual faults, wrong cadence, altered geometry and truncation.

## Original spatial gates and signed interactions

The exact original 54 metrics use the fixed 65x9x65 support, original
normalizations, difference limit 0.01, increment-ratio limit 0.7 and analysis
cutoff 1e-8. Dense field increments on full common 83x9x113 support are
reported separately. No observable, threshold or failed result is removed.
The two bulk-potential increments below are measured on the original
support. The original absolute increment limit for this observable is
250 microV. These increments are not absolute solution-error bounds.

| Steps per phase | Time (ps) | z113 to z121 increment (microV) | z121 to z129 increment (microV) |
| --- | ---: | ---: | ---: |
| 128 | 0 | 451.667603 | 172.192079 |
| 128 | 20 | 546.627347 | 208.356497 |
| 128 | 40 | 425.183063 | 162.094240 |
| 128 | 60 | 484.289132 | 184.617916 |
| 256 | 0 | 451.667603 | 172.192079 |
| 256 | 20 | 546.616980 | 208.352530 |
| 256 | 40 | 425.198435 | 162.100123 |
| 256 | 60 | 484.278558 | 184.613869 |

The [interaction report](space_time_interaction.json) subtracts signed
arrays on exact nested 83x9x113 support before taking norms:

`[u(z_fine,dt/2)-u(z_coarse,dt/2)] - [u(z_fine,dt)-u(z_coarse,dt)]`.

Of forty field/phase/pair metrics, **26/40** exceed the inherited
**1e-08** normalized analysis floor. The maximum normalized mixed
increment is **9.22706973e-07**. This describes resolved interactions;
it supplies no new acceptance gate, decoupling claim or error bound.

| Time (ps) | z113 to z121 mixed bulk potential (V) | z121 to z129 mixed bulk potential (V) |
| --- | ---: | ---: |
| 20 | 1.55542736e-08 | 9.84445751e-09 |
| 40 | 2.30676743e-08 | 1.45999124e-08 |
| 60 | 1.58588875e-08 | 1.00366022e-08 |

The [time-trace report](time_trace_diagnostics.json) applies the unchanged
interval-matched comparator to ending-time states, BE interval currents and
signed cumulative terminal charges, including gate edges, on all three z
grids. The inherited z113 comparison reproduces the x83 study exactly.
Two time resolutions supply increments, not a temporal order estimate.

## Scope and next controls

Only these four new pulses are counted; the two z113 controls are inherited
once. All owned workers exited. Solver and trace tests (245 and 25) are
inherited by unchanged hashes with zero reruns. No solver source was changed,
and native, production, calibration and the protected 1078-file original
inventory remain unchanged. No version was published or deployed.

Local contact-grid refinement does not supply a uniform global h ratio.
Original local x and z endpoint gates, and the earlier y controls, do not
establish a joint x/y/z error bound. A further time level on the refined
geometry, combined spatial controls and an explicit observable error budget
remain necessary. Earlier coarse-x failures remain sealed in the
[x75 study](../20261107-geometric-x75-time/README.md). General 2D logic,
memory and material qualification, quantum transport and complete Sentaurus
equivalence remain open.

See [matrix scope](matrix_audit.json), [frozen policy](policy.json),
[provenance](PROVENANCE.json), [reproduction](reproduction/README.md) and
[hashes](MANIFEST.json).
