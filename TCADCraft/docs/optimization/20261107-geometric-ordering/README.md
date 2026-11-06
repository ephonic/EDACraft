# Geometric ordering for the captured y33 Newton system

**An opt-in `GEOMETRIC_ND` ordering passes 245 targeted regressions and the
captured 239,745-row y33 matrix check.** This is an unreleased development
change. The prior [3,600 s y33 capacity failure](../20261106-third-y-probe/README.md)
is retained; a completed y33 device probe is still required.

## Usage and solver contract

Use these constructor options on `DielectricSheetDriftDiffusion`:

```python
electrostatic_backend='coupled',
linear_solver='reused_gmres',
linear_ordering='GEOMETRIC_ND',
```

The geometry-only recursive plane separator places interior subdomains first
and each separator last. It maps the independent sheet phi/Fn/Fp variables
and free dielectric potentials to their node coordinates, including repeated
sheet coordinates. Balanced thin separators limit the cost of cutting
through the sheet. Small leaves retain original index order.

The preconditioner factors `A[p][:, p]` with SuperLU `NATURAL` ordering;
right-hand sides and returned solutions are mapped through the same immutable
permutation. Cache identity includes its contents, the selected ordering and
the steady/backward-Euler operator including exact dt. Published factors and
permutations are shared read-only across driver copies. Factorization errors
retain the accepted transient state and its factor.

`COLAMD` remains the default, and `MMD_AT_PLUS_A` remains available. Harmonic
bulk initialization uses its original sparse solve. All physical equations,
GMRES iteration/refresh limits, nonlinear gates and true original-system
row-scaled max-norm bound `min(1e-14, 0.01*tolerance)` remain unchanged.
[AST checks](source_checks.json) compare the original acceptance, correction,
single-refresh and error code and the frozen prototype's ordering algorithm.

## Isolated measurements

The matrix was captured immediately before the first DC factorization after
the original initializer on x65/y33/z113, with representative isothermal MoS2,
traps and finite electrodes. It has **1,668,115 nonzeros**, 242,385 bulk nodes
and 2,145 sheet nodes. Capture stops before any accepted DC/BE state.

The initializer took **368.96 s** wall time and
254.36 s process CPU, with **6251.35 MiB**
process peak RSS. This measures a new observational replay, not the stages of
the preceding timed-out process. The captured [profile](capture.profile.jsonl)
keeps both timings and samples.

Each subsequent matrix trial ran once in a fresh, single-threaded process
on the recorded host. Per-child limits were frozen at 900 s wall/CPU,
48 GiB address space and 32 GiB peak RSS.

| Captured-matrix measurement | Prototype | Integrated option |
| --- | ---: | ---: |
| Geometry ordering (s) | 1.576 | 0.395 |
| Linear solve including factorization (s) | 218.429 | 157.718 |
| Peak process RSS through solve (MiB) | 4146.81 | 4128.62 |
| True original scaled residual max norm | 4.44089e-16 | 4.44089e-16 |

The prototype's separately timed factorization took 216.029 s.
Its factors contain 172,779,061 L and 147,916,139 U entries. Exporting
these statistics after solving raised process peak RSS to
7039.03 MiB; this export is excluded from
the through-solve RSS entry. The integrated trial does not export L/U.
RSS includes the runtime and is not a measurement of LU allocation alone.

The integrated permutation matches the frozen prototype; solution bitwise
equality is **true** on this host.
Independent local row sums give 4.44089e-16
(float64) and 3.68087e-16 (extended precision).
These supplementary sums do not replace the original solver guard.
See [prototype verification](prototype_verification.json) and
[integrated verification](integration_verification.json).

The prototype temporarily substitutes the factorization inside an original
MMD-labelled context, so its inherited diagnostic label is explicitly
marked as such. The integrated option uses its own `GEOMETRIC_ND` label and
has no prototype monkeypatch. No like-for-like completed MMD solve of this
matrix was measured here; no baseline speedup or whole-device runtime/RSS
claim follows from these two trials.

## Correctness and remaining qualification

**245 tests passed**, zero failures, errors or skips: all 223 previous
targeted regressions were rerun, plus 22 new cases. New coverage includes
complete deterministic separator permutations, immutable cache keys,
nonsymmetric vector/multicolumn/integer/complex mapping against dense solves,
ordering/permutation/dt invalidation, injected factorization failure rollback,
and graphene linear/Dirac and MoS2 thermionic trap pulses with variable dt,
independent flux/terminal checks and MMD physical comparisons.
See [JUnit results](targeted_tests.xml).

This study adds **zero large-device accepted steps and zero complete pulses**.
The capture and both matrix solves receive no full-device physics credit.
The original 26 y9/y17/y33 metrics remain unevaluated. Next run a bounded
initial/first-BE y33 probe with the integrated option and unchanged physical
gates, followed by consistent three-grid and full-pulse controls before
fine-grid temporal and joint space/time qualification.

The native binary, protected original source, failed parent evidence and
production installation retain their recorded identities. All owned workers
have exited. The full development test suite was not run. No native rebuild,
commercial run, release or production deployment was performed. General 2D
logic/memory, calibrated material/contact models, quantum transport and full
Sentaurus equivalence remain outside this study's qualification.

Use the [portable replay instructions](reproduction/README.md),
[provenance](PROVENANCE.json) and [file hashes](MANIFEST.json).
