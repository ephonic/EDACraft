# Explicit sheet linear-cache release; large replay remains open

`SheetTransient.clear_linear_cache()` explicitly releases the driver's optional
Newton preconditioner between steps and returns whether a cached factor was
present. The next linear solve rebuilds it with the existing tolerances.
Accepted state, time and drive are unchanged. Default cache behavior,
equations, factorization, GMRES and residual guards are unchanged. The method
does not clear the dielectric Schur factor or mutate another driver's shared
immutable factor.

**223 regressions pass, including 8 new tests. The large y17 replay is rejected
because it reaches its frozen 1,800 s wall limit before completing the first
BE step. The earlier memory-budget failure is not closed by this attempt.**

## Regression coverage and large-grid observations

The new tests verify actual lifetime of the sole cached factor, isolation of
shared driver copies, graphene/MoS2 and three contact families, physical parity
over variable dt, factor reuse after rebuilding, and state/drive/time rollback
after factor-allocation or nonlinear failures following explicit release.
The other 215 tests cover reused GMRES, ordering, coupled electrostatics,
finite contacts and sheet transient behavior. [JUnit results](tests.xml) are
from the exact source hashes recorded in [provenance](PROVENANCE.json).

The new isolated solve uses the same 65 x 17 x 113 geometry, representative
isothermal MoS2/trap/contact inputs, SI float128 native binary, MMD ordering,
dt 0.15625 ps, nonlinear `1e-12` and true row-scaled linear max norm `1e-14`.
The driver adds only one cache-release call after its initial checkpoint;
the frozen launcher proves the remaining driver AST is unchanged. A second
AST check proves the source addition is confined to the new method.

The completed initial checkpoint matches its previously independently audited
baseline **bit for bit: 39 arrays, 11,897,640 array bytes and 159 scalar values**.
No expected differences are excluded from this initial comparison. This is
initial-state parity, not first-BE or complete-history parity. There are
**zero newly completed dynamic steps and zero new complete pulses**.
No new independent physics-check count is credited from reused audit evidence.

Read-only process observations straddle initial-state completion and explicit
cache release:

| Elapsed (s) | Saved checkpoints | Process RSS (MiB) | Observed high-water RSS (MiB) |
| ---: | ---: | ---: | ---: |
| 1195.50 | 0 | 2524.42 | 2895.11 |
| 1268.82 | 1 | 683.31 | 2895.11 |
| 1728.22 | 1 | 1952.41 | 2895.11 |

These [sampled observations](resource_observations.json) are transcribed from
the read-only status tool output. They show a reduction in resident memory
after the initial checkpoint and release, but are **not final whole-process
peak RSS or a completed memory-budget acceptance**. Do not compare them as
the final peak against the inherited 6,311.34 MiB result. Other temporary
allocations can also change between phases.

## Frozen failure and audit boundary

The original 1,800 s wall, 16 GiB address-space and 6,144 MiB RSS budgets were
retained. The worker terminates the child at the wall limit and preserves its
traceback and atomic initial checkpoint. No first-BE checkpoint, accepted-step
journal or final full export exists. The frozen acceptance auditor rejects
the failure marker. A separate timeout auditor checks initial byte parity,
archive/source identities and worker termination; it does not override the
failed acceptance verdict. All owned test/probe workers have exited and the
production target and files remain unchanged.

The [audit](independent_audit.json), [frozen policy](policy.json),
[source/archive identities](PROVENANCE.json), [hashes](MANIFEST.json) and
[exact replay](reproduction/README.md) retain the distinction between tested
API behavior and incomplete large-grid qualification. The
[previous y17 memory failure and x/y study](../20261106-independent-xy-probes/README.md)
remain unchanged.

## Use and next work

```python
# After constructing a SheetTransient and saving initial fields:
released = run.clear_linear_cache()
result = run.step(dt_s=dt, **drive)
```

Use release between steps when lowering retained-factor memory is useful.
Clearing before every step sacrifices reuse. Another live driver copy may
retain the factor, and the allocator need not return freed memory to the OS
immediately. This API does not guarantee a memory cap for arbitrary meshes or
factor refreshes.

Next, profile factorization/GMRES CPU and wall costs and complete the full y17
initial/first-BE replay under a policy declared before the next launch. Any
different wall budget must be reported as a new policy; this original timeout
remains failed. Complete-pulse x/y studies, another independent y increment
and joint space/time qualification remain open. General 2D logic/memory,
calibrated materials, quantum transport and full Sentaurus equivalence are
not established. No deployment or new version was published.
