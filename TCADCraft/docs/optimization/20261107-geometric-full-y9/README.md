# Complete geometric-ordering y9 control

**A fresh `GEOMETRIC_ND` y9 control completes all 384 backward-Euler steps
and the full 60 ps pulse, passing the original independent physical, ledger,
linear and resource gates.** This supplies the first full control for the
same-ordering y sequence. Full y17/y33 trajectories and the original 54-metric
three-grid y convergence verdict remain pending.

## Frozen run and outcome

The x65/y9/z113 case uses the exact driver bytes from the
[same-ordering prefix study](../20261107-geometric-probes/README.md), invoked
with `full` instead of `probe`. It retains the representative isothermal MoS2
sheet, traps, finite thermionic side contacts, 0.15625 ps BE steps and all
drive phases. Initial and phase-end fields are exported at 0/20/40/60 ps.
The initial cache is explicitly cleared once before the first BE step;
subsequent accepted steps retain the storage-operator cache.

Before launch, the budget was frozen at 3,600 s wall/CPU, 6 GiB process peak
RSS and 48 GiB address space, with one numerical thread. The nonlinear limit
remains `1e-12`; every accepted linear solve must satisfy the original
row-scaled max-norm `1e-14` gate. No numerical source or acceptance formula changed.

| Measurement | Result |
| --- | ---: |
| Bulk / sheet nodes | 66,105 / 585 |
| Whole-run wall time | 1020.776 s |
| Peak process RSS | 604.90 MiB |
| Maximum nonlinear residual | 9.9099693e-13 |
| Newton linear solves / LU factorizations | 894 / 2 |
| GMRES iterations / corrections / refreshes | 5965 / 645 / 0 |
| Independent physical and ledger checks | 780,479 |

These are single-run host measurements, not a general performance guarantee.

## Independent acceptance and comparisons

The sealed full-pulse checker audits all 384 step ledgers and 385 linear
diagnostics, as well as the four complete field checkpoints. It checks sheet
statistics and transport, trap storage, dielectric flux/Poisson equations,
contact charges, electrostatic energy and terminal-current consistency.
Atomic checkpoint files and the accepted-step journal match the final record.
See the [independent audit](independent_audit.json) and
[complete linear records](linear_records.json).

The original MMD full y17 result was replayed before launch. Its verdict,
check count and physical maxima were reproduced exactly with the adapted
ordering-label checker. A synthetic ND label replay and nine corruption tests
were also accepted/rejected as expected. Corruptions cover interior trace
charge, dt, accepted linear residual, final bulk potential, middle-phase gate
drive, x/y geometry, cache protocol and wrong ordering. These tool replays
receive zero new simulation or physics credit. See [tool checks](auditor_tool_checks.json).

The initial full field and the first two trace/diagnostic entries match the
sealed y9 ND probe bit for bit. The full driver does not export the first-BE
complete field, so first-BE full-field parity is not claimed.

The [ordering comparison](ordering_control_differences.json) reports 54
normalized observable differences against the retained MMD full y9 run, at
the same 0/20/40/60 ps times on common 65x9x65 nodes. The largest descriptive
difference is `7.9379003e-12`. This is a same-grid comparison with
no new acceptance gate; it is not a three-grid convergence result.

The [full-trajectory comparison](full_trajectory_ordering_differences.json)
also reports absolute differences for every node in the four complete fields,
all accepted-time scalar traces, and cumulative BE terminal charges. Initial
current entries are excluded because they do not represent an accepted BE
interval. Drive arrays, geometry and accepted clocks must match exactly.

## Reproduction and remaining work

This study contributes **one complete pulse, 384 BE steps and four complete
field checkpoints**. Numerical sources are unchanged from the 245 passing
targeted tests, inherited by exact source hashes; those tests were not rerun.
Native, production, calibration and all 1,078 protected original-source files
were checked. All owned workers exited.

Next run full same-ordering y17/y33 controls, then evaluate the unchanged
54 phase-end y metrics. Fine-grid temporal and joint space/time qualification
remain open. This case does not establish general 2D logic/memory operation,
material/contact calibration, quantum transport or Sentaurus equivalence.
No release or production deployment was performed.

See [frozen policy](policy.json), [replay instructions](reproduction/README.md),
[provenance](PROVENANCE.json) and [file hashes](MANIFEST.json).
