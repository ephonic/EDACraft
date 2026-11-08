# Three-z-grid / three-time-step full-pulse matrix

Two new complete 60 ps MoS2 pulses at x83/y9/z113 and x83/y9/z121, with
512 BE steps per phase, fill the two missing corners of a **nine-pulse matrix**.
The seven other complete pulses are inherited from the
[z/time study](../20261108-geometric-z-time/README.md), the
[x83 study](../20261107-geometric-x83-time/README.md), and the
[refined z129 three-time study](../20261108-geometric-fine-time512/README.md).
All new pulses pass independent physics, all-step ledgers, nonlinear,
true-linear and resource gates. Original spatial verdicts are shown below
without modifying thresholds. Joint error bounds remain open.

## Frozen protocol and independent checks

Both drivers are byte-identical to their own sealed n128/n256 parents. Only
the CLI count changes to 512: dt 0.0390625 ps, 1536 BE steps per pulse and
full fields at 0/20/40/60 ps. Representative isothermal MoS2 parameters,
thermionic contacts, traps, GEOMETRIC_ND ordering, cache release and the
SI float128 native extension are unchanged. All nine corners share the same
291 solver-source files, seven test-source files and native identity.

Each new case runs serially with one numerical thread, frozen 6000 s wall/CPU,
4 GiB RSS and 48 GiB address-space limits. Nonlinear residual 1e-12 and
row-scaled true-linear max norm 1e-14, iteration and refresh limits are retained.

| New control | Whole-run time (s) | Peak RSS (MiB) | Maximum nonlinear residual |
| --- | ---: | ---: | ---: |
| geometric_z113_n512 | 2376.5264 | 758.29297 | 9.7904157e-13 |
| geometric_z121_n512 | 2994.9144 | 888.07422 | 9.7774362e-13 |

The [physical audit](independent_audit.json) adds
**2,089,230 physical and ledger checks** over
**3072 fresh steps, two fresh pulses and eight fresh full fields**. It reconstructs
sheet statistics and transport, traps, dielectric Poisson/flux and electrostatic
energy, contact charges, terminal currents and every accepted-step ledger.
Initial fields and linear diagnostics match each mesh's n128 parent bit for bit.
Each new trajectory rejects thirteen corruptions, including late charge/residual
faults, wrong cadence, geometry, ordering and truncation. First-BE parity across
different dt is not claimed.

Prelaunch [auditor checks](auditor_tool_checks.json) reproduce the sealed
z129 n512 and z121 n256 physical summaries and maxima exactly. The
[diagnostic checks](diagnostic_tool_checks.json) reproduce 108 original spatial
metrics, forty signed mixed metrics, all twenty full-field and 54 original-support
three-time metrics and the complete z129 trace report. Analytic and fault tests,
and all replays, earn zero new simulation credit.

## Unchanged spatial gates at all three dt

The [spatial report](spatial_diagnostics.json) applies the original 54 observables
on fixed 65x9x65 support, scales 0.025 V / 1e-18 C / 1e-7 A (occupancy scale 1),
normalized difference limit 0.01, ratio limit 0.7 and cutoff 1e-8. Dense common
83x9x113 field changes are separate. Both inherited n128/n256 reports reproduce
exactly; all failures, if any, remain visible.

| Steps per phase | Original gates passed | Failures |
| --- | ---: | ---: |
| 128 | 54/54 | 0 |
| 256 | 54/54 | 0 |
| 512 | 54/54 | 0 |

| Steps per phase | Time (ps) | z113 to z121 bulk increment (microV) | z121 to z129 bulk increment (microV) |
| --- | ---: | ---: | ---: |
| 256 | 20 | 546.61698 | 208.35253 |
| 256 | 40 | 425.19843 | 162.10012 |
| 256 | 60 | 484.27856 | 184.61387 |
| 512 | 20 | 546.61184 | 208.35056 |
| 512 | 40 | 425.20605 | 162.10304 |
| 512 | 60 | 484.27331 | 184.61186 |

The original bulk increment limit is 250 microV. These adjacent increments are
measured differences, not absolute errors. The [54-observable inventory](observable_increment_inventory.json)
now includes a matched spatial increment at n512 and temporal increments on
each z mesh; it does not sum them into an error bound.

## Temporal and signed mixed increments

The unchanged [three-time field formula](three_time_fields.json) reports
`log2(d128_256/d256_512)` for twenty full-field phase metrics and 54 original
observables on each mesh. It uses the inherited 1e-8 normalized floor. The z129
field report reproduces its sealed predecessor exactly.

| z nodes | Time (ps) | n128 to n256 bulk increment (microV) | n256 to n512 bulk increment (microV) | Observed order |
| --- | ---: | ---: | ---: | ---: |
| 113 | 20 | 6.2292944 | 3.088173 | 1.0123152 |
| 113 | 40 | 10.307778 | 5.1056485 | 1.0135672 |
| 113 | 60 | 6.619147 | 3.2873435 | 1.0097231 |
| 121 | 20 | 6.2280997 | 3.08757 | 1.0123202 |
| 121 | 40 | 10.305857 | 5.1046742 | 1.0135736 |
| 121 | 60 | 6.6181047 | 3.286814 | 1.0097283 |
| 129 | 20 | 6.2275629 | 3.0872991 | 1.0123224 |
| 129 | 40 | 10.304993 | 5.104236 | 1.0135765 |
| 129 | 60 | 6.6176363 | 3.286576 | 1.0097306 |

The [signed interaction report](space_time_interaction.json) evaluates
`[u(zfine,dt/2)-u(zcoarse,dt/2)]-[u(zfine,dt)-u(zcoarse,dt)]`
on exact nested 83x9x113 support, subtracting arrays before taking norms.
There are forty metrics per time pair, eighty total; resolved counts are
{'128_256': 26, '256_512': 24}. The inherited forty entries reproduce exactly.
Pair 0 is z113 to z121; pair 1 is z121 to z129. The mixed-norm order below
is a descriptive change under dt halving, not a spatial order or a decoupling gate.

| z pair | Time (ps) | n128/n256 mixed bulk increment (V) | n256/n512 mixed bulk increment (V) | Mixed-norm order |
| --- | ---: | ---: | ---: | ---: |
| 0 | 20 | 1.5554274e-08 | 7.7107987e-09 | 1.0123588 |
| 0 | 40 | 2.3067674e-08 | 1.1425654e-08 | 1.0135958 |
| 0 | 60 | 1.5858887e-08 | 7.8758637e-09 | 1.0097815 |
| 1 | 20 | 9.8444575e-09 | 4.8802763e-09 | 1.0123489 |
| 1 | 40 | 1.4599912e-08 | 7.2315475e-09 | 1.0135834 |
| 1 | 60 | 1.0036602e-08 | 4.9844272e-09 | 1.0097713 |

The [trace comparator](three_time_trace.json) retains the same 384 coarse ending
times and physical intervals for both increments, including gate edges and
signed cumulative charges. All three inherited two-time traces and the complete
z129 three-time trace reproduce exactly. Adjacent checkpoint clock tolerance
remains 1e-24 s; three-way accumulated spread is reported separately.

| z nodes | Trace category | Resolved / metrics | Resolved decreasing |
| --- | --- | ---: | ---: |
| 113 | state_at_common_times | 12/12 | 12 |
| 113 | interval_average_currents_and_rates | 8/8 | 8 |
| 113 | conduction_at_common_ending_times | 2/2 | 2 |
| 113 | cumulative_current_and_rate_integrals | 8/8 | 8 |
| 121 | state_at_common_times | 12/12 | 12 |
| 121 | interval_average_currents_and_rates | 8/8 | 8 |
| 121 | conduction_at_common_ending_times | 2/2 | 2 |
| 121 | cumulative_current_and_rate_integrals | 8/8 | 8 |
| 129 | state_at_common_times | 12/12 | 12 |
| 129 | interval_average_currents_and_rates | 8/8 | 8 |
| 129 | conduction_at_common_ending_times | 2/2 | 2 |
| 129 | cumulative_current_and_rate_integrals | 8/8 | 8 |

## Scope and remaining work

Three dt provide observed temporal orders on every z mesh, with no declared
asymptotic regime or absolute error bound. Local contact-grid node counts do not
define a uniform global h ratio. Combined x/y/z controls and an explicit physical
observable tolerance budget remain necessary for joint qualification. Coarse-x
failures remain sealed in the [x75 study](../20261107-geometric-x75-time/README.md).
No threshold, support or failed result was removed.

Only two new pulses are credited. Seven matrix pulses, 245 solver tests and
25 trace tests are inherited by hashes, with zero test reruns. All owned workers
exited. Solver/native, production, calibration and the protected 1078-file
inventory are unchanged. No release was published or deployed. General 2D
logic/memory/material and quantum-transport qualification, the previously excluded
research areas and full Sentaurus equivalence remain open.

See [matrix scope](matrix_audit.json), [policy](policy.json),
[provenance](PROVENANCE.json), [reproduction](reproduction/README.md) and
[hashes](MANIFEST.json).
