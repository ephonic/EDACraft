# First complete independent-y pulse

The **65 x 17 x 113** MoS2/trap/finite-contact case completes the full
**60 ps** pulse with **384 accepted backward-Euler steps** and four full
field checkpoints at **0/20/40/60 ps**. This extends the earlier y17
initial/first-step probe to all three pulse phases. It supplies one full
y9/y17 refinement increment; a third y mesh is still required for a ratio.

| Quantity | Result |
| --- | ---: |
| Bulk / sheet nodes | 124,865 / 1,105 |
| Wall time | 3269.21 s |
| Final process peak RSS | 4026.01 MiB |
| Maximum nonlinear scaled residual | 9.76977805e-13 |
| Independent physical and ledger checks | 1,496,479 |
| Accepted linear diagnostic records | 385 |
| Newton linear solves / factorizations | 887 / 2 |

The predeclared budget remains 3,600 s wall/CPU, 16 GiB address space and
6,144 MiB peak RSS, with serial execution and one BLAS/OpenMP thread. The
driver AST is identical to the sealed explicit-release y17 probe; only the
CLI mode selects the complete pulse. The representative isothermal material,
contacts, traps, dt 0.15625 ps, SI float128 native binary, MMD ordering,
nonlinear tolerance `1e-12` and true row-scaled linear max norm `1e-14` remain.
The optional DC cache is released once before the first dynamic solve.

## Independent audit and parity

All accepted-step charge/current/storage/integral ledgers and all four full
field checkpoints pass the independent physical oracle. Atomic checkpoints,
accepted linear journal, progress and final exports agree. Eight corrupted
variants are rejected: interior trace charge, dt, linear residual, bulk field,
gate drive, x geometry, y geometry and cache invalidation flag.

Only the oracle's expected x/y arrays are substituted by a reversible AST
transformation. The prelaunch replay reproduces the inherited full-pulse
ledger result and count and rejects all eight corruptions, receiving zero
new simulation credit. The cache guard requires false invalidation flags
at every solve, then delegates the other checks to the unchanged guard on a
temporary diagnostic copy. Raw physical records are unchanged.

The initial full state, first two scalar trace entries and first two linear
diagnostics match the inherited y17 probe bit for bit after its expected
first-BE invalidation flag changes from true to false. This covers
39 arrays / 11,897,640 array bytes and
348 scalar values. The first-BE full field is not saved by
the full driver and is not claimed as a field parity comparison.

Numerical source is unchanged; 223 solver regressions are inherited by exact
source hashes and were not rerun. All owned workers exited. Original source,
candidate, test, native and production identities were reverified. Earlier
short-probe memory and timeout failures remain preserved in the
[profile report](../20261106-cache-profile/README.md).

## Full y9/y17 changes

The inherited x65/y9/z113 full pulse and this x65/y17/z113 pulse share all
385 clock entries exactly. The original 54 normalized endpoint changes use
the established 65 x 9 x 65 common support. Additional full-coarsest-mesh
changes cover all shared 65 x 9 x 113 nodes. Both use exact shared nodes
without interpolation. The dense projection's saved-phase loop extension
replays the sealed short-y comparison exactly.

| Time (ps) | Bulk change on original support (mV) | Bulk change on full shared mesh (mV) | Original normalized energy change |
| --- | ---: | ---: | ---: |
| 0 | 0.00020584861 | 0.00020584861 | 2.59103165e-06 |
| 20 | 0.000195390755 | 0.000195390755 | 2.62856655e-06 |
| 40 | 0.00021132649 | 0.00021132649 | 2.47233141e-06 |
| 60 | 0.000204004672 | 0.000204004672 | 2.64533637e-06 |

Selected full-trajectory changes:

| Observable | Maximum absolute change | Time (ps) |
| --- | ---: | ---: |
| `sheet_charge_C` (C) | 1.18226e-24 | 40 |
| `trap_charge_C` (C) | 4.25486e-24 | 54.5313 |
| `dielectric_energy_J` (J) | 6.75444e-26 | 22.1875 |
| `total/drain` (A) | 5.37802e-14 | 20.1562 |

These two-mesh changes are descriptive, with no new acceptance gates or
convergence ratio. [Original endpoint changes](spatial_diagnostics.json)
and [full common fields / scalar trajectory changes](supplementary_diagnostics.json)
retain the complete values. Full fields are available at four endpoints,
not every accepted time step.

## Reproduction and remaining scope

[Driver and mesh](reproduction/README.md), [policy](policy.json),
[physical audit](independent_audit.json), [checker replay](auditor_tool_checks.json),
[projection replay](diagnostic_tool_check.json), [identities](PROVENANCE.json)
and [hashes](MANIFEST.json) accompany this report. The preceding
[x69/x75/x83 endpoint sequence](../20261106-full-x-sequence/README.md)
retains its separate 54/54 result.

A second independent y increment, fine-grid temporal refinement and joint
space/time qualification remain open. This representative case does not
qualify general 2D logic/memory, real-material calibration, quantum transport
or full Sentaurus equivalence. No native rebuild, commercial run, production
deployment or new release was performed.
