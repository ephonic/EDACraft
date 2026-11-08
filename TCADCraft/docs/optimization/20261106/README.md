# Sheet solver optimization — 2026-11-06

This is an **unreleased development change** on top of `0.3.0rc1`.
The tagged wheel and production installation are unchanged.

## Optional LU ordering

For a coupled dielectric sheet device, set both
`linear_solver='reused_gmres'` and `linear_ordering='MMD_AT_PLUS_A'`.
`COLAMD` remains the default. The option changes the Newton preconditioner's
SuperLU column ordering. Harmonic initialization and direct/Schur solves keep
their existing behavior. Nondefault ordering requires the reused-GMRES backend.

The cache includes the selected ordering in addition to its steady/BE storage
operator. An ordering change discards an incompatible candidate preconditioner;
an exception or rejected step retains the accepted history and factor. The
original true row-scaled max-norm limit `min(1e-14, 0.01*tolerance)`, verified
residual correction and single LU refresh remain enforced.

## Captured-system measurements

The included phase-two fixture has 37,737 equations and 258,829 nonzeros.
Each ordering ran once in a fresh single-threaded process on the same host.
RSS was sampled after solving, before extracting L/U statistics. It includes
interpreter/runtime memory and is not the LU allocation size.

| Metric | COLAMD | MMD_AT_PLUS_A |
| --- | ---: | ---: |
| L + U nonzeros | 24,070,448 | 10,169,229 |
| Solve time (s) | 3.512 | 1.361 |
| Peak process RSS through solve (MiB) | 366.12 | 218.59 |
| True scaled residual max norm | 9.4369e-15 | 3.38618e-15 |

This fixture showed 57.8% fewer factor nonzeros,
40.3% lower process peak RSS and a
2.58× elapsed speedup. These are single-run measurements,
not universal performance guarantees. Full large-mesh pulses with the new
ordering remain to be measured. See [raw benchmark](linear_ordering_benchmark.json).

## Correctness checks

- **215 targeted tests passed**, zero failures/errors/skips: new ordering
  validation, cache invalidation, variable dt, graphene/MoS2/Dirac contact
  pulses, independent flux/current checks, and existing rollback controls.
- The 65×9×65 candidate initial state and one BE step passed **226,547**
  independent physical checks and **1,315,764** comparisons against default
  ordering using the original sealed comparison limits. The largest potential
  difference was below `8e-16 V`; trap occupancy differed below `4e-15`.
- The unchanged published SI float128 native extension was reused; only two
  Python solver files changed. The full development suite was not rerun.
- An earlier new constructor test omitted required mobility arguments:
  214 passed/1 failed. The input was corrected, the failed attempt retained,
  and all 215 tests passed on the final candidate.

See [candidate verification](candidate_verification.json),
[independent physics audit](ordering_physics_audit.json) and
[JUnit results](targeted_tests.xml).

## Spatial diagnosis

Four fresh SI initial/one-BE probes independently varied x, y or z from a
65×9×65 base, adding **4 steps, 8 complete fields and 1,554,492 independent
physical checks**. A corrupted internal field was correctly rejected.
The first-step changes in dielectric potential were about 741 µV (x),
0.207 µV (y), and 1615 µV (z). Signed x/z contributions partially cancel for
some sheet observables, so combined-grid differences alone can hide their
separate effects. Local contact-z refinement is supported as a direction for
further study; one refinement does not establish convergence order.

Original spatial failures remain open. Full-pulse directional/local-z, fine-grid
time and joint spacetime acceptance, calibrated material/contact parameters,
complete logic/memory workflows and dedicated quantum transport remain open.
See [directional diagnosis](directional_diagnosis.md),
[full comparison summary](directional_summary.json) and
[source/evidence provenance](PROVENANCE.json).
