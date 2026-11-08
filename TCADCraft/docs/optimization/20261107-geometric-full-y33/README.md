# Full geometric y33 pulse and three-grid y endpoint sequence

**The fresh full y33 pulse passes its original independent physical, ledger,
linear and resource gates. The complete same-ordering y9/y17/y33 endpoint
sequence passes the original convergence test: 54/54 metrics pass.**
The verdict applies to the saved phase endpoints at fixed x65/z113, with the
original observation support and tolerances. Global spatial, fine-grid time
and joint space/time qualification remain open.

## Frozen experiment and resources

The x65/y33/z113 case uses the exact accepted
[prefix driver](../20261107-geometric-probes/README.md) bytes in full mode:
384 BE steps of 0.15625 ps through 60 ps, representative isothermal MoS2,
traps and finite thermionic side electrodes. Full fields are exported at
0/20/40/60 ps; every step has scalar, progress and linear journals. Only the
initial steady-state cache is explicitly released before transient stepping.

Before launch, the resource budget was frozen at 14,400 s wall/CPU, 32 GiB
process peak RSS and 48 GiB address space, with one numerical thread. The
accepted y33 prefix had taken 951 s and 6.10 GiB RSS. This is a separately
declared full-run budget; earlier MMD failures remain preserved. The nonlinear
`1e-12`, original row-scaled linear max-norm `1e-14`, iteration and refresh
gates are unchanged.

| y nodes | Whole-run wall time (s) | Peak process RSS (MiB) |
| --- | ---: | ---: |
| 9 | 1020.776 | 604.90 |
| 17 | 1251.754 | 1827.23 |
| 33 | 3285.333 | 6253.18 |

The y9/y17 rows are inherited accepted full controls, not new runs in this
study. These are single-run host measurements, not a general speedup claim.
The new y33 case uses 242,385 bulk and 2,145 sheet nodes;
its maximum nonlinear residual is `9.662159e-13`.
There are 875 Newton linear solves, 2 LU
factorizations, 5999 GMRES iterations,
637 corrections and 0 refreshes.

## Independent acceptance and actual convergence verdict

The [new y33 audit](independent_audit.json) contributes
**2,928,479 new physical and ledger checks**, covering
all 384 BE ledgers, 385 linear diagnostics and the complete field exports:
sheet statistics/transport, traps, dielectric Poisson and fluxes, contact
charges, electrostatic energy and terminal currents. Atomic checkpoints and
accepted-step journals match the final record. Nine corruptions of interior
charge, dt, linear residual, bulk field, gate drive, x/y geometry, cache
protocol and ordering are rejected.

The initial full field and first two trace/diagnostic entries match the
accepted ND y33 prefix bit for bit. The full driver does not export the
first-BE full field, so that field's parity is not claimed. No accepted full
MMD y33 result exists; [same-grid MMD comparison](ordering_control_differences.json)
is explicitly unavailable.

The [sequence audit](sequence_audit.json) combines the new pulse with the
sealed [y9](../20261107-geometric-full-y9/README.md) and
[y17](../20261107-geometric-full-y17/README.md) full controls. Its cohort total
is 5,205,437 checks across three complete pulses;
the two inherited pulses and their checks receive no new credit.

The unchanged [54-metric function](derived/inherited_metric_function.py)
uses fixed common 65x9x65 nodes at 0/20/40/60 ps, the original normalization,
last increment `<0.01` and ratio `<0.7` when the preceding increment exceeds
the `1e-8` roundoff floor. Passing 54-metric and failing 26-metric retained
fixtures reproduce their sealed verdicts exactly before launch. See
[convergence tool checks](convergence_tool_checks.json) and
[physical tool checks](auditor_tool_checks.json).

Metric failures: None.

[Spatial diagnostics](spatial_diagnostics.json) retain every metric and
supplementary absolute field changes on all common 65x9x113 nodes at the four
saved endpoints, plus descriptive all-step scalar increments. The dense
projection and trace differences add no acceptance gate. The field convergence
verdict covers the four saved phase endpoints; it is not an all-time field
or joint convergence certificate.

## Scope and remaining work

This study contributes **one new complete pulse, 384 BE steps and four full
fields**. Numerical sources match the 245 passing targeted tests; those tests
are inherited by exact source hashes and were not rerun. Native, production,
calibration and 1,078 protected original-source files are unchanged. All owned
workers have exited; no release or deployment was performed.

Fine-grid temporal and joint space/time qualification remain to be completed;
any failed y metrics listed above also remain open. This representative
isothermal DD study does not establish calibrated material/contact models,
general 2D logic/memory operation, quantum transport, three-temperature
experimental validation or complete Sentaurus equivalence.

Use [frozen policy](policy.json), [wrapper derivation](wrapper_derivation.json),
[replay instructions](reproduction/README.md), [provenance](PROVENANCE.json)
and [report hashes](MANIFEST.json).
