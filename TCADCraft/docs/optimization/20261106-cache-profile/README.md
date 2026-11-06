# Completed profiled y17 cache-release replay

The **65 x 17 x 113** initial/first-BE replay now completes and passes
independent physical checks and the 6 GiB RSS gate under a **separately declared
3,600 s wall/CPU policy**. The prior [1,800 s timeout](../20261106-linear-cache-release/README.md)
and the older [retained-cache memory failure](../20261106-independent-xy-probes/README.md)
remain failed and unchanged. This new result does not retroactively accept
either attempt.

| Configuration | Wall seconds | Final peak process RSS (MiB) | Verdict |
| --- | ---: | ---: | --- |
| Inherited retained-DC-cache probe | 668.01 | 6311.34 | Failed 6 GiB RSS |
| Prior explicit-release attempt | 1800 limit | unavailable | Timed out before first BE |
| New explicit-release + observational profiling | 539.34 | 4031.98 | Passed new declared policy |

Final process peak RSS is **36.12% lower** than
the inherited retained-cache measurement. These are single runs under their
prevailing host conditions, not a repeated speed benchmark. The new run includes
profiling overhead. Its measured wall time is 539.34 s; the policy
remains 3,600 s regardless of whether this observation is below the old limit.

Numerical source matches development commit `7c9550b`;
no new solver changes or native rebuild were made. The same geometry, physical
inputs, post-DC cache-release call, dt 0.15625 ps, MMD ordering, 16 GiB address
space, 6,144 MiB RSS gate, nonlinear `1e-12` and true row-scaled linear max norm
`1e-14` remain. The driver adds only observational installation statements,
with the remaining AST proven identical to the sealed explicit-release driver.

## Physical and cache parity

**745,923 new independent physical/ledger checks pass.**
The sealed physical checker is unchanged. Six deliberately corrupted variants
(charge, dt, linear residual, bulk field, gate drive and y geometry) are rejected.
Atomic checkpoints, accepted-step journal and final export agree. One dynamic
step and two field checkpoints are new; there are **zero new complete pulses**.

The inherited linear guard assumes automatic first-BE cache invalidation.
An explicit adapter strictly requires the predeclared false flag at both
checkpoints, then delegates every other check to that unchanged guard on a
temporary diagnostic copy. Raw exports and physical fields are untouched;
two additional unexpected-invalidation corruptions are rejected. The first
audit attempt's protocol mismatch is preserved in the raw archive.

The complete exported record and linear diagnostics match the inherited
retained-cache probe bit for bit after the sole expected first-BE diagnostic
flag `invalidated_initial_factor` changes from true to false. Literal checks
cover **104 arrays / 34,738,408 array bytes** and
630 scalar values. The physical fields themselves require no
normalization, interpolation or excluded differences.

The 223 solver regressions are inherited from the exact source hashes and were
not rerun. A separate profiling tool check compares the captured linear
fixture and a small MoS2 trap trajectory with and without instrumentation;
all exported fields and diagnostics agree exactly. It gets zero large-grid
simulation credit. All owned workers exited; native and production identities
were reverified.

## Where the work goes

Initial bulk Poisson: 26.130 s wall /
25.857 s CPU. The remaining measured stages are:

| Phase | Event | Completed calls | Wall seconds | CPU seconds |
| --- | --- | ---: | ---: | ---: |
| DC | linear_solve | 7 | 219.725 | 217.924 |
| DC | newton_factorization | 1 | 163.462 | 162.127 |
| DC | gmres | 14 | 56.218 | 55.749 |
| DC | triangular_solve | 238 | 55.214 | 54.769 |
| BE | linear_solve | 4 | 289.077 | 288.076 |
| BE | newton_factorization | 1 | 277.289 | 276.326 |
| BE | gmres | 7 | 11.764 | 11.727 |
| BE | triangular_solve | 41 | 11.659 | 11.622 |

These times are **nested, not additive**: triangular preconditioner solves
are inside GMRES, and factorization/GMRES are inside linear solves. Event
begin/end stacks, sequence numbers, phase labels and diagnostic call counts
are checked. [Timing details](profile_summary.json) retain all groups;
the complete event log and live monitor snapshots are in the sealed raw
archive identified by [provenance](PROVENANCE.json).

## Reproduction and remaining scope

[Exact driver, profiler and mesh](reproduction/README.md), [policy](policy.json),
[physical audit](independent_audit.json), [profiler check](profiler_tool_checks.json)
and [hashes](MANIFEST.json) accompany this report. No LU factor matrices are
materialized just to measure fill, and wrappers forward original arguments
and numeric returns unchanged. This is a diagnostic experiment, not a
default profiling change in the solver.

This closes the initial/first-BE y17 replay under the new declared policy;
it does not establish y convergence, full-pulse x/y acceptance, joint space/time
qualification, material calibration, general 2D logic/memory, quantum transport
or full Sentaurus equivalence. Complete x69/x75/x83 and y17 pulses, another
independent y increment and joint studies remain. No production deployment
or new version was published.
