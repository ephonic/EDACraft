# Full y33 half-dt pulse

**The fresh 60 ps pulse on x65/y33/z113 passes the original independent
physical, all-step ledger, linear and resource gates at 0.078125 ps dt.**
Together with the sealed [0.15625 ps control](../20261107-geometric-full-y33/README.md),
it provides two complete time resolutions on the same mesh. Two resolutions
measure an increment; observed temporal order and fine-grid temporal
qualification remain open until the third resolution is evaluated.

## Frozen protocol and outcome

The numerical driver bytes, geometry, representative isothermal MoS2 material,
traps, finite thermionic electrodes, drive phases, SI float128 native extension
and GEOMETRIC_ND ordering are identical to the accepted full y33 control.
Only CLI steps per phase changes from 128 to 256. This adds 768 BE steps,
with complete fields at 0/20/40/60 ps and scalar/linear journals for every step.
The initial steady-state linear cache is explicitly cleared before stepping.

The predeclared budget is 21,600 s wall/CPU, 32 GiB process peak RSS and
48 GiB address space, with one numerical thread. It is a separate bounded
experiment based on the inherited 3,285 s full pulse and doubled step count.
The nonlinear `1e-12`, original row-scaled true linear max-norm `1e-14`,
iteration limits and refresh policy remain unchanged.

| Measurement | Result |
| --- | ---: |
| Bulk / sheet nodes | 242,385 / 2,145 |
| Complete steps / full fields | 768 / 4 |
| Whole-run wall time | 5929.807 s |
| Peak process RSS | 6251.10 MiB |
| Maximum nonlinear residual | 9.8195769e-13 |
| Newton linear solves / LU factorizations | 1654 / 2 |
| GMRES iterations / corrections / refreshes | 10812 / 1148 / 0 |
| New independent physical / ledger checks | 2,933,087 |

These are single-run host measurements and establish no general speedup.

## Independent checks and time-step observations

The [independent audit](independent_audit.json) reconstructs the complete
saved fields and all 768 step ledgers, and checks 769 linear diagnostics,
atomic exports and accepted-step journals. Physical checks cover sheet
statistics/transport, traps, dielectric Poisson/flux, electrostatic energy,
contact charges and terminal currents. The initial full field, scalar state
and linear diagnostics match the accepted same-mesh n128 control bit for bit.
Different dt values do not imply first-BE parity.

The [auditor tool replay](auditor_tool_checks.json) reproduces the sealed
full y33 n128 result and the original physical oracle/linear guard on an
inherited n256 trajectory. The three wrapper cadence constants are replaced
reversibly with predeclared expected counts; physical formula bytes are unchanged.
Thirteen faults are rejected, including late fine-step charge/residual
corruption beyond step 384, tail truncation and wrong cadence. Replay and
deliberate corruptions receive zero new physics credit.

The [full-grid field comparison](two_time_fields.json) uses every node of
each same-mesh field at 0/20/40/60 ps, and separately retains the original
54 normalized increments on fixed 65x9x65 support. Selected absolute changes:

| Time (ps) | Maximum bulk-potential change (microV) | Maximum trap-occupancy change |
| --- | ---: | ---: |
| 20 | 6.232111 | 1.207862e-05 |
| 40 | 10.31229 | 1.563353e-05 |
| 60 | 6.621592 | 7.583078e-06 |

The [whole-trace comparison](two_time_trace.json) compares scalar states at
common ending times and BE currents over matching coarse physical intervals,
including gate-edge impulses and signed integrated terminal charges. Its
unchanged comparator exactly reproduces the sealed older three-time result
before launch; [tool identity](diagnostic_tool_checks.json) records the proof.
The original adjacent-clock gate is retained. These two-time differences
are descriptive and introduce no acceptance threshold or observed order.

## Scope and replay

This study contributes one new complete pulse, 768 steps and four full fields;
the n128 parent is inherited and counted once. The 245 targeted solver tests
and 25 trace tests are inherited by exact hashes, with zero reruns. Native,
production, calibration and 1,078 protected original-source files are unchanged.
All owned workers exited. No release or deployment was performed.

Next obtain the third same-mesh resolution (512 steps per phase) for temporal
orders. Global spatial and joint space/time qualification, calibrated models,
general 2D logic/memory, quantum transport and complete Sentaurus equivalence
remain open. See [diagnostic scope](temporal_diagnostics.json),
[policy](policy.json), [replay](reproduction/README.md),
[provenance](PROVENANCE.json) and [hashes](MANIFEST.json).
