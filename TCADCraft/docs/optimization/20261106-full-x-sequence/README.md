# Complete x69/x75/x83 endpoint sequence

The **x69/x75/x83** sequence passes **54 / 54** original
complete-pulse endpoint metrics at **0/20/40/60 ps**, with y9/z113 fixed.
Two new MoS2/trap/finite-contact trajectories supply **768 accepted BE steps**
and eight full field checkpoints. The x69 trajectory is inherited and receives
zero new simulation credit.

| Complete 60 ps pulse | Wall time (s) | Final peak process RSS (MiB) |
| --- | ---: | ---: |
| x69 (inherited) | 882.33 | 1146.57 |
| x75 (new) | 867.48 | 1193.46 |
| x83 (new) | 1141.26 | 1372.18 |

Both new cases pass their predeclared 3,600 s wall/CPU, 16 GiB address-space
and 6,144 MiB peak-RSS budgets. Execution is serial with one BLAS/OpenMP thread.
The exact representative isothermal material, traps, finite contacts, dt
0.15625 ps, MMD ordering, SI float128 native binary, nonlinear `1e-12` and
true row-scaled linear max norm `1e-14` remain. The driver changes only its
x coordinate selector; explicit cache release follows DC once.

## Independent physics and source identity

**1,896,846 new independent physical/ledger checks pass.**
Every accepted-step charge/current/storage/integral ledger and all eight
new endpoint fields are checked. Atomic checkpoints, progress, accepted
linear journal and final exports agree. Each case rejects eight corrupted
variants: interior trace charge, dt, linear residual, bulk potential, gate
drive, x geometry, y geometry and cache invalidation flag.

Initial full fields, first-BE scalar trace and linear diagnostics match each
inherited short probe bit for bit after the sole declared cache invalidation
flag change. The first-BE full field is not saved by the full driver and is
not claimed as a parity comparison. Numerical source is unchanged; 223 solver
regressions are inherited by exact source hashes and were not rerun. Native
and production identities were reverified and all owned workers exited.

A case audited while the next case runs is reused only after all 14 case
files match the final archive exactly. Its live snapshot's pending-credit
flag records the capture stage; the final cohort credits its checks once.

## Original endpoint gates

All 54 observables use the established **65 x 9 x 65 common nodes**, unchanged
normalization and no interpolation. The final normalized difference must be
below `0.01`; its ratio to the preceding increment must be below `0.7` when
the preceding increment exceeds the `1e-8` floor. These localized mesh
increments do not define a uniform-grid convergence order.

The convergence function is extracted without AST changes from the sealed
earlier endpoint analysis. Before launch, it reproduces both the inherited
54-metric passing z sequence and the earlier x probe's failed metric exactly.
That tool replay receives zero new simulation credit.

| Time (ps) | x69 to x75 bulk change (mV) | x75 to x83 (mV) | Increment ratio |
| --- | ---: | ---: | ---: |
| 0 | 0.235124536 | 0.0413844759 | 0.176011 |
| 20 | 0.284252734 | 0.0500922273 | 0.176224 |
| 40 | 0.221327444 | 0.0389602313 | 0.17603 |
| 60 | 0.252022398 | 0.0443751215 | 0.176076 |

Failed endpoint metrics: None.

[All metric values](spatial_diagnostics.json) retain the verdict and failures.
All three full pulses have exactly matching 385 clock entries. Maximum
accepted-trace changes and their times are descriptive; no new trajectory
convergence threshold is introduced. The older x65/x69/x75 short-probe failure
and all previous resource/time failures remain preserved.

The newly available older full x65/x69/x75 sequence has
**52 / 54** endpoint metrics passing; its full verdict
and failed values are retained in [supplementary diagnostics](supplementary_diagnostics.json).
This older sequence does not replace the declared x69/x75/x83 sequence.

For additional coverage, all shared **69 x 9 x 113** nodes give these bulk
potential changes (descriptive; the frozen acceptance policy is unchanged):

| Time (ps) | x69 to x75 (mV) | x75 to x83 (mV) |
| --- | ---: | ---: |
| 0 | 0.420789963 | 0.118683885 |
| 20 | 0.509151649 | 0.143660687 |
| 40 | 0.396066944 | 0.111718229 |
| 60 | 0.451160264 | 0.12726402 |

The dense projection changes only the inherited loop's saved-phase inventory;
reversing its AST transformation is exact. A [tool replay](dense_projection_tool_check.json)
recovers the sealed short-probe dense changes exactly, with zero new simulation credit.

Selected full-trajectory changes (descriptive, in the stated physical units):

| Observable | Max x69 to x75 change | Time (ps) | Max x75 to x83 change | Time (ps) |
| --- | ---: | ---: | ---: | ---: |
| `sheet_charge_C` (C) | 5.40862e-22 | 7.5 | 9.43465e-23 | 7.5 |
| `trap_charge_C` (C) | 2.63176e-24 | 20 | 4.60074e-25 | 20 |
| `dielectric_energy_J` (J) | 8.35735e-23 | 0.15625 | 1.42907e-23 | 0.15625 |
| `total/drain` (A) | 9.04881e-10 | 20.1562 | 1.53363e-10 | 20.1562 |

## Reproduction and remaining scope

[Drivers and exact mesh](reproduction/README.md), [policy](policy.json),
[physical audit](independent_audit.json), [checker replay](auditor_tool_checks.json),
[identities](PROVENANCE.json) and [hashes](MANIFEST.json) accompany this report.
The [first full x69 pulse](../20261106-first-full-x-pulse/README.md) retains its
independent history. This verdict covers the representative local x sequence
at four complete-pulse endpoints. Interior scalar trajectory differences
are descriptive, and full fields are not saved at every step.

Full y17 and another independent y increment, fine-grid temporal refinement,
joint space/time qualification, material calibration, general 2D logic/memory,
quantum transport and full Sentaurus equivalence remain open. No native
rebuild, commercial run, production deployment or new version was published.
