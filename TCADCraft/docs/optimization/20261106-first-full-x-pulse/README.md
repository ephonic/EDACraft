# First complete endpoint-x pulse

The **69 x 9 x 113** MoS2/trap/finite-contact case completes the full **60 ps**
pulse: **384 accepted BE steps** and four complete field checkpoints at
0/20/40/60 ps. This fills the first complete-pulse slot in the planned
x69/x75/x83 sequence. It is not a three-grid x convergence result.

| Quantity | Result |
| --- | ---: |
| Bulk / sheet nodes | 70,173 / 621 |
| Wall time | 882.33 s |
| Final process peak RSS | 1146.57 MiB |
| Maximum nonlinear scaled residual | 9.87261296e-13 |
| Independent physical and ledger checks | 828,463 |
| Accepted linear diagnostic records | 385 |
| Newton linear solves / factorizations | 894 / 2 |

The predeclared budget is 3,600 s wall/CPU, 16 GiB address space and
6,144 MiB final peak RSS, with serial execution and one BLAS/OpenMP thread.
The same representative isothermal material/contact/trap parameters, dt
0.15625 ps, SI float128 native binary, MMD ordering, nonlinear `1e-12` and
true row-scaled linear max norm `1e-14` remain. Explicit cache release occurs
once after DC; the BE factor is then reused transactionally between steps.

## Independent audit and inherited parity

Every accepted-step charge/current/storage/integral ledger and all four full
field checkpoints pass. Atomic checkpoints, the accepted linear journal,
progress and final exports agree. Eight deliberately corrupted variants are
rejected: interior trace charge, dt, linear residual, bulk potential, gate
drive, x geometry, y geometry and cache invalidation flag.

The frozen independent oracle substitutes only the exact expected x/y arrays;
reversing the AST transformation recovers the inherited oracle exactly.
An inherited-data tool check proves identical ledger results/counts and
rejects all eight corruptions before launch. It receives zero new simulation
credit. The cache adapter strictly requires the declared false invalidation
flag, delegating every other check to the unchanged retained-cache guard on
a temporary diagnostic copy. No raw physical data are adapted.

The initial full state, first two scalar trace entries and first two linear
diagnostics match the inherited x69 short probe bit for bit, after the sole
expected first-BE invalidation flag changes from true to false. This covers
39 arrays / 6,570,920 array bytes and
348 scalar values. The full driver saves phase endpoints;
**a first-BE full-field comparison is unavailable and is not claimed**.

Numerical source is unchanged from the source already covered by 223 solver
regressions; those tests were not rerun. All owned workers exited, source and
native identities were reverified, and production target/files are unchanged.

## First full x increment

The inherited MMD x65/y9/z113 full pulse and this x69/y9/z113 pulse share
all 385 clock entries exactly. The following changes use the established
65 x 9 x 65 common support and original normalization. No interpolation,
new gate, convergence ratio or order estimate is introduced.

| Time (ps) | Bulk potential change (mV) | Normalized dielectric-energy change |
| --- | ---: | ---: |
| 0 | 0.748745957 | 0.00847023362 |
| 20 | 0.904897235 | 0.0102965679 |
| 40 | 0.704741733 | 0.00713910284 |
| 60 | 0.802485344 | 0.00886995765 |

[All 54 normalized endpoint changes](spatial_diagnostics.json) are descriptive.
Full x75 and x83 pulses are still required to evaluate the consecutive
three-grid sequence with the original difference/ratio gates. The older
[short-probe failures and later probe improvement](../20261106-independent-xy-probes/README.md)
remain preserved. Full y17, another independent y increment and joint
space/time qualification also remain open.

## Reproduction and scope

[Exact driver and mesh](reproduction/README.md), [frozen policy](policy.json),
[audit](independent_audit.json), [prelaunch checker test](auditor_tool_checks.json),
[identities](PROVENANCE.json) and [hashes](MANIFEST.json) accompany this report.
The [preceding y17 initial/first-BE memory replay](../20261106-cache-profile/README.md)
remains a short probe. This new complete x69 pulse does not qualify full x/y
convergence, joint space/time behavior, general 2D logic/memory, real-material
calibration, quantum transport or full Sentaurus equivalence. No native
rebuild, production deployment or new version was published.
