# Complete geometric-ordering y17 control

**The full y17 `GEOMETRIC_ND` pulse passes the original independent physics,
all-step ledger, linear and resource gates.** Together with the
[full y9 control](../20261107-geometric-full-y9/README.md), it supplies two
complete same-ordering trajectories. Full y33 and the original 54-metric
three-grid y convergence verdict remain pending.

## Frozen experiment and outcome

The x65/y17/z113 case uses the exact bytes of its accepted
[prefix driver](../20261107-geometric-probes/README.md), invoked in full mode.
It retains representative isothermal MoS2 statistics, traps, finite thermionic
side contacts, all three drive phases and 0.15625 ps BE steps. Complete fields
are exported at 0/20/40/60 ps; all 384 accepted steps have scalar and linear
journals. The steady-state cache is explicitly released once before the first
BE step; the storage-operator cache is retained thereafter.

Before launch, the budget was frozen at 7,200 s wall/CPU, 6 GiB peak RSS and
48 GiB address space, with one numerical thread. The earlier MMD full y17
run took about 3,269 s and the ND prefix about 157 s; this new full ordering
therefore has a separately declared budget. Prior failures remain preserved.
The nonlinear `1e-12` and original row-scaled linear max-norm `1e-14` limits,
iteration limits and refresh policy remain unchanged.

| Measurement | Result |
| --- | ---: |
| Bulk / sheet nodes | 124,865 / 1,105 |
| Complete BE steps / field checkpoints | 384 / 4 |
| Whole-run wall time | 1251.754 s |
| Peak process RSS | 1827.23 MiB |
| Maximum nonlinear residual | 9.7716748e-13 |
| Newton linear solves / LU factorizations | 887 / 2 |
| GMRES iterations / corrections / refreshes | 6016 / 649 / 0 |
| Independent physical and ledger checks | 1,496,479 |

These are single-run host measurements and do not establish a general speedup.

## Independent acceptance and retained comparisons

The [independent audit](independent_audit.json) checks all 385 linear
diagnostics and 384 BE ledgers, plus the complete field checkpoints: sheet
statistics and transport, traps, dielectric Poisson and fluxes, contacts,
field energy and terminal-current consistency. Atomic exports and accepted
linear journals match the final record. Nine deliberate corruptions of
interior charge, dt, linear residual, final bulk field, middle-phase gate
drive, x/y geometry, cache protocol and ordering are rejected.

Before execution, the inherited full MMD y17 result reproduced its original
verdict, check count and physical maxima exactly. A synthetic ND metadata
replay tested the label parameterization; replayed steps receive zero new
physics credit. The [wrapper derivation](wrapper_derivation.json) records
reversible substitutions from the sealed y9 audit wrapper; the independent
physical formula and ordering guard source hashes remain identical.
See [auditor tools](auditor_tool_checks.json) and [linear records](linear_records.json).

The initial field and first two trace/linear entries match the accepted ND
y17 prefix bit for bit. The full run does not export the first-BE complete
field, so first-BE full-field parity is not claimed.

The [same-grid ordering comparison](ordering_control_differences.json)
reports 54 normalized differences against full MMD y17, with maximum
`2.1693689e-12`. The [full-trajectory comparison](full_trajectory_ordering_differences.json)
adds all-node differences at four checkpoints, scalar traces and cumulative
BE terminal charges. These comparisons introduce no acceptance gate.

The [two-grid y diagnostics](spatial_diagnostics.json) report 54 y9/y17
increments using the original normalization and fixed 65x9x65 observation
support. The same diagnostic function reproduces the sealed MMD increments
exactly. Two ND grids provide no three-grid ratio or convergence verdict.

## Remaining qualification and replay

This study contributes **one new complete pulse, 384 BE steps and four full
field checkpoints**. Numerical sources match the 245 passing targeted tests;
those tests are inherited by exact hashes and were not rerun. Native,
production, calibration and 1,078 protected original-source files are unchanged.
All owned workers have exited; no release or deployment was performed.

Next complete the full same-ordering y33 trajectory and evaluate the original
54-metric sequence. Fine-grid temporal and joint space/time qualification,
calibrated material/contact models, general 2D logic/memory operation, quantum
transport and complete Sentaurus equivalence remain open.

See [frozen policy](policy.json), [replay instructions](reproduction/README.md),
[provenance](PROVENANCE.json) and [report hashes](MANIFEST.json).
