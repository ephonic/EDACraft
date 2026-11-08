# Complete-pulse ordering and local contact-z follow-up

The optional MMD ordering passed a complete 60 ps MoS2 sheet pulse against a
fresh default-ordering control. A third complete pulse used a nested local
contact-z mesh. This validates the tested classical solver trajectories;
spatial convergence and complete device qualification remain open.

## Execution and resources

All three cases used the same tested development source, unchanged SI float128
native extension, one BLAS/OpenMP thread, original physical parameters, 128 BE
steps per 20 ps phase, and three drive phases. Each case ran once, serially,
in a fresh process. The base grid is 65 x 9 x 65; the local grid is 65 x 9 x 81.
There are 585 sheet nodes in both. The finite contacts retain their physical
5 nm bounds; no flux or charge rescaling was applied.

| Case | Total nodes | Seconds | Peak process RSS (MiB) | Newton linear solves | LU factors | LU refreshes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| base_colamd | 38,025 | 326.08 | 668.54 | 894 | 2 | 0 |
| base_mmd | 38,025 | 210.23 | 417.00 | 894 | 2 | 0 |
| local_z1_mmd | 47,385 | 312.81 | 704.46 | 894 | 2 | 0 |

For this one full-pulse base-grid pair, elapsed speedup was
**1.551x** and peak process RSS reduction was
**37.6%**. These measurements
include the unchanged harmonic initialization, all nonlinear iterations,
diagnostics and output encoding. RSS includes the interpreter/runtime; it
is not LU allocation size. The earlier captured-Jacobian result measured a
different scope and cannot be substituted for this full-pulse comparison.
No 282,897-node MMD full pulse has been run.

## Independent acceptance

- **3 complete pulses, 1,152 new dynamic steps and 12 full field checkpoints**.
  Complete fields were saved at initialization and 20/40/60 ps, with the
  preceding state at each dynamic checkpoint. This is not an every-step
  full-field audit.
- **1,480,765 independent physics and ledger
  checks**. The sealed equations rebuild 2D carrier statistics, bulk/sheet
  finite-volume fluxes, contact/gate charges, trap BE kinetics and terminal
  currents. Every scalar step is checked for Gauss balance, charge partition,
  displacement/conduction KCL, storage rates and integrated charge balance.
- **3,060,680 physical parity constraints** between
  the fresh base-grid orderings passed the original sealed tolerances. This
  does not assert bitwise equality.
- All 1,155 accepted linear diagnostic records passed the existing true
  row-scaled max-norm limit `1e-14`; nonlinear tolerance remains `1e-12`.
  Seven deliberate corruptions were rejected, including an interior time-step
  ledger, internal bulk field, drive, prior state, progress and linear residual.
- The numerical source is unchanged from the candidate with 215 passing
  targeted tests. Those tests are inherited, not rerun or added to this
  follow-up's new check count. The full suite was not rerun.

## Local refinement observations

Absolute changes from the base MMD grid to local-z level 1, at common nodes:

| Time (ps) | Sheet potential (microV) | Dielectric potential (microV) | Trap occupancy | Dielectric energy (J) |
| --- | ---: | ---: | ---: | ---: |
| 0 | 121.071 | 1290.565 | 0.000678128 | 3.9018e-22 |
| 20 | 133.323 | 1562.807 | 0.000724596 | 4.73275e-22 |
| 40 | 113.718 | 1215.042 | 0.000673438 | 3.29755e-22 |
| 60 | 125.878 | 1384.013 | 0.000688511 | 4.07816e-22 |

The audit also records differences to the inherited all-axes fine-grid full
pulse. That comparison changes x and y as well as z, so it does not isolate z
error or establish convergence order. Local-z level 2 has only an initial/one-BE
probe so far. A second complete local refinement and independent directional
full pulses, followed by fine-grid temporal and joint spacetime tests, remain
necessary. Original spatial acceptance failures are retained.

## Reproduction and scope

Use `linear_solver='reused_gmres', linear_ordering='MMD_AT_PLUS_A'` with the
coupled dielectric sheet backend. COLAMD remains the default. Tagged
`0.3.0rc1` artifacts and production are unchanged.

The compact evidence here includes [independent acceptance](independent_audit.json),
[frozen execution policy](policy.json), [resources](resources.json),
[derived sealed oracle](derived_full_pulse_oracle.py) and
[source/archive identities](PROVENANCE.json). Full JSON/NPZ fields, per-step
progress/linear records and launch scripts remain in the development validation
archive identified by the provenance record; raw arrays are not bundled here.

The model remains isothermal, with representative uncalibrated homogeneous
material bands and constant mobility. Material/contact calibration, complete
logic/memory workflows, quantum transport and Sentaurus equivalence have not
been established by these numerical checks.
