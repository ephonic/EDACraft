# Complete endpoint-z pulses and second x probe

Two new complete 60 ps MoS2 pulses and one initial/first-BE x probe passed
independent physical audits. The endpoint-z sequence passes **54 / 54**
local phase metrics; the independent x sequence passes **25 / 26**
initial/first-step metrics. These results extend the
[earlier short endpoint probes](../20261106-temporal-endpoint/README.md).

## Complete execution and independent audit

The numerical solver source, representative isothermal MoS2/trap/contact
parameters and SI float128 native extension are unchanged. Runs were serial
with one BLAS/OpenMP thread and optional MMD preconditioner ordering.

| New case | Grid | New dynamic steps | Seconds | Peak process RSS (MiB) |
| --- | --- | ---: | ---: | ---: |
| endpoint_x2_probe | 75 x 9 x 113 | 1 | 85.68 | 1963.49 |
| endpoint_z1_n128 | 65 x 9 x 121 | 384 | 969.22 | 2049.17 |
| endpoint_z2_n128 | 65 x 9 x 129 | 384 | 1010.07 | 2382.77 |

There are **768 new full-pulse steps**, one new probe step and ten new full-field
checkpoints. Fields are independently audited at saved checkpoints; all
accepted-step linear records and dynamic conservation ledgers are checked.
There are **2,170,237 new independent physical/ledger checks**.
Six deliberate corruptions are rejected: interior charge ledger, dt, linear
residual, bulk field, gate drive and probe x coordinates. A separate checker
replay on inherited full/probe data also rejects these faults and receives no
new simulation credit. The [checker identity proof](checker_identity.json)
verifies inventory-only changes and sealed physical dependencies. Neither
inherited tests nor live audits are double-counted.

The nonlinear residual limit remains `1e-12`; the true row-scaled linear
residual max norm remains `1e-14`. Budgets frozen before launch were 4,800 s
per full pulse, 900 s for the probe, 16 GiB address space and 6 GiB peak RSS.
All owned workers exited. Numerical/native identities and production target
and files were reverified. No native rebuild, release or deployment occurred.

## Endpoint-z full pulses at 0/20/40/60 ps

The sequence has 113 inherited z nodes and 121/129 endpoint-refined z nodes.
x/y remain 65/9. All records use 128 BE steps per 20 ps phase, dt 0.15625 ps.
The reference full pulse is inherited and audited; only the two endpoint
pulses are new. The new initial states and first accepted step exactly match
the corresponding inherited short probes, including linear diagnostics.

All increments use the same original **65 x 9 x 65** nodes. Inherited physical
scales and gates remain `0.01` normalized difference, `0.7` increment ratio and
`1e-8` roundoff floor. For bulk potential, the difference gate is 0.25 mV.
Ratios are measured between this localized sequence's successive increments;
they are not observed orders for a uniform global mesh family.

| Time (ps) | z113 to z121 bulk change (mV) | z121 to z129 (mV) | Increment ratio |
| --- | ---: | ---: | ---: |
| 0 | 0.220038 | 0.0520485 | 0.236544 |
| 20 | 0.266366 | 0.063002 | 0.236524 |
| 40 | 0.20714 | 0.0489963 | 0.236538 |
| 60 | 0.235948 | 0.0558108 | 0.236538 |

Remaining full-z local metrics:

- None in this local diagnostic.

The [diagnostics](spatial_diagnostics.json) include sheet phi/Fn/Fp, traps,
terminal/gate charges and currents, and dielectric energy. Descriptive scalar
trace changes cover all 385 accepted times (initial plus 384 steps), with a
maximum matched clock difference of `0 s`.
Their current differences are at identical dt and times, including gate jumps;
no extra trace acceptance limit or extrapolated error bound is introduced.

The previous broader z65/z81/z113 sequence's four failed bulk-potential metrics
remain preserved in its [original report](../20261106-contact-z-time/README.md).
The endpoint-specific study supplies new complete-pulse evidence without
changing that history or its gates. Independent x/y and joint spatial/time
qualification remain separate.

## Independent x refinement: initial and first BE step only

The x sequence is 65/69/75 nodes with fixed parent z113 and y9. The new x75
probe bisects six x69 cells in 0.25 nm neighborhoods of the source/drain planes.
Every old coordinate and all physical contact bounds are preserved. The x65
reference is the inherited sealed SI probe; its ordering predates optional
MMD, while physical parameters and native profile match. x69 is inherited from
the previous endpoint study. Neither reference is credited as a new solve.

| Time (ps) | x65 to x69 bulk change (mV) | x69 to x75 (mV) | Increment ratio |
| --- | ---: | ---: | ---: |
| 0 | 0.748746 | 0.235125 | 0.314024 |
| 0.15625 | 0.937946 | 0.29445 | 0.313931 |

Remaining x-probe metrics under the unchanged gates:

- `1_dielectric_phi_V`

This short x study cannot establish complete-pulse x acceptance. The minimum
x75 spacing is approximately 0.030114 nm; minimum endpoint-z spacings remain
0.0390625/0.01953125 nm. They probe a continuum discretization near an ideal
contact edge, not an atomistic resolution or material-accuracy claim.

## Reproduction and limits

[Exact drivers and mesh](reproduction/README.md), [frozen policy](policy.json),
[audit](independent_audit.json), [checker replay](checker_replay.json),
[resources](resources.json), [provenance](PROVENANCE.json) and
[file hashes](MANIFEST.json) accompany the record. Raw fields and accepted-step
journals remain in the local archive identified in provenance.

There are no numerical product changes in this study. The 215 solver tests
and 25 postprocessing tests are inherited, not rerun. Local acceptance does
not establish global spatial convergence, joint space/time qualification,
general 2D logic/memory capability, material calibration, quantum transport,
general energy/entropy closure or full Sentaurus equivalence.
