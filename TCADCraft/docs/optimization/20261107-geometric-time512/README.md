# Full y33 three-resolution time study

The fresh 60 ps pulse on x65/y33/z113 passes the original independent physical,
all-step ledger, nonlinear, true linear-residual and resource gates at
**0.0390625 ps dt**. Together with the sealed
[n128](../20261107-geometric-full-y33/README.md) and
[n256](../20261107-geometric-time256/README.md) controls, it provides three
complete time resolutions and descriptive observed BE orders on this mesh.
Asymptotic, general temporal, global spatial and joint space/time qualification
remain open; three resolutions alone establish no error bound.

## Frozen protocol and measured outcome

The driver bytes, geometry, representative isothermal MoS2 parameters, traps,
finite thermionic contacts, three 20 ps phases, SI float128 native extension
and GEOMETRIC_ND ordering are unchanged. Only the CLI steps per phase changes
to 512. The initial linear cache is explicitly cleared before stepping.

The predeclared budget is 21,600 s wall/CPU, 32 GiB peak process RSS, 48 GiB
address space and one numerical thread, based on the prior 5,930 s n256 run.
The nonlinear `1e-12` and original row-scaled true linear max-norm `1e-14`
limits, iteration limits and refresh policy remain unchanged.

| Measurement | Result |
| --- | ---: |
| Bulk / sheet nodes | 242,385 / 2,145 |
| New accepted BE steps / full fields | 1,536 / 4 |
| Whole-run wall time | 10328.369 s |
| Peak process RSS | 6252.54 MiB |
| Maximum nonlinear residual | 9.9214846e-13 |
| Newton linear solves / LU factorizations | 3205 / 2 |
| GMRES iterations / corrections / refreshes | 19936 / 2480 / 0 |
| New independent physical / ledger checks | 2,942,303 |

These are single-run host measurements and establish no general speedup.

## Independent checks and observed orders

The [independent audit](independent_audit.json) reconstructs all saved fields,
all 1,536 step ledgers and 1,537 linear diagnostics, atomic exports and accepted
step journals. It checks sheet statistics/transport, traps, dielectric Poisson
and flux, electrostatic energy, contact charges and terminal currents.
Initial full fields, scalar state and linear diagnostics match the same-mesh
n128 control bit for bit. First-BE parity is not claimed across different dt.

The [auditor replay](auditor_tool_checks.json) exactly reproduces the sealed
full y33 n128 summary and the original parameterized physical oracle and linear
guard on inherited n256 and n512 trajectories. Only three wrapper inventory
constants are adapted reversibly. Physical formula bytes are unchanged.
Thirteen deliberate corruptions are rejected on the n512 fixture and on the
new trajectory, including charge/residual faults after step 1,024, truncated
tails and wrong cadence. Replays and corruptions receive zero new physics credit.

The [full-field report](three_time_fields.json) computes max-norm increments
and `log2(d01/d12)` at every saved node for sheet phi/Fn/Fp, trap occupancy and
bulk potential at 0/20/40/60 ps. The field-order formula [replay](field_order_tool_checks.json), performed after
launch, matches 140 metric values from the sealed older study and passes four explicit
roundoff/order cases. The unchanged normalized floor `1e-8` marks
unresolved orders. It separately reports the original 54 metrics on fixed
65x9x65 support; original spatial gates are not reused as temporal acceptance.

| Time (ps) | n256 to n512 bulk-potential change (microV) | Bulk-potential order | Trap-occupancy order |
| --- | ---: | ---: | ---: |
| 20 | 3.0896 | 1.0123 | 0.997499 |
| 40 | 5.10794 | 1.01355 | 0.981367 |
| 60 | 3.28859 | 1.00971 | 0.983689 |

The [whole-trace report](three_time_trace.json) uses the original comparator,
which [reproduces](diagnostic_tool_checks.json) the sealed older three-resolution
trace before launch. Both increments use the same 384 ending times and coarse
physical intervals. BE current averages include gate-edge impulses, and signed
cumulative terminal charges are compared. Adjacent physical-clock gates retain
`1e-24 s`; three-way accumulated clock spread is reported separately.
Observed orders describe these data and do not establish an asymptotic regime.

## Scope and reproduction

This study adds one new complete pulse, 1,536 steps and four full fields. The
two parents are inherited and counted once. The 245 solver and 25 trace tests
are inherited by exact source hashes, with zero reruns. All owned workers
exited. Native, production, calibration and 1,078 protected original-source
files are unchanged. No deployment, publication or native rebuild occurred.

Further spatial/time combinations and an explicit error budget are needed for
joint qualification. Calibrated materials, general 2D logic/memory, quantum
transport, experimental validation and complete Sentaurus equivalence remain
outside this result. See [scope](temporal_diagnostics.json), [policy](policy.json),
[replay](reproduction/README.md), [provenance](PROVENANCE.json) and
[hashes](MANIFEST.json).
