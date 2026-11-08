# Refined x83/y9/z129 three-time-resolution full pulse

The new complete 60 ps MoS2 pulse at **0.0390625 ps dt** passes the unchanged
independent physical, all-step ledger, nonlinear, true-linear and resource
gates on x83/y9/z129. Together with sealed n128 and n256 controls in the
[z/time study](../20261108-geometric-z-time/README.md), this supplies three
complete time resolutions on the refined geometry. Observed orders describe
these trajectories; an asymptotic regime and a joint error bound remain open.

## Frozen protocol and measured result

Driver bytes are identical to both accepted parents. Only the CLI count
changes to 512 steps per 20 ps phase. Representative isothermal MoS2 parameters,
traps, finite thermionic contacts, GEOMETRIC_ND ordering, explicit initial-cache
release and the SI float128 native extension are unchanged. Full fields are
saved at 0/20/40/60 ps. The predeclared budget is 6000 s wall/CPU, 4 GiB peak
RSS, 48 GiB address space and one numerical thread, based on the same-grid
n256 run (1318.556 s, 996.85 MiB). Original nonlinear 1e-12 and row-scaled
true-linear max-norm 1e-14 limits, iteration caps and refresh policy are retained.

| Measurement | Result |
| --- | ---: |
| Bulk / sheet nodes | 96,363 / 747 |
| New BE steps / full fields | 1,536 / 4 |
| Whole-run time | 2803.783 s |
| Peak process RSS | 988.53 MiB |
| Maximum nonlinear residual | 9.7535777e-13 |
| Newton linear solves / LU factorizations | 3214 / 2 |
| GMRES iterations / corrections / refreshes | 19597 / 2237 / 0 |
| New physical / ledger checks | 1,147,767 |

These are single-run measurements, with no general speedup claim.

## Independent verification and temporal increments

The [physical audit](independent_audit.json) reconstructs sheet statistics and
transport, traps, dielectric Poisson/flux and electrostatic energy, contact
charges, terminal currents and every step ledger. Initial full fields and
linear diagnostics match the n128 parent bit for bit. Thirteen corruptions
are rejected, including charge/residual faults after step 1024, truncation,
wrong cadence, altered geometry and ordering. First-BE parity across dt is
not claimed.

Before launch, the [physical replay](auditor_tool_checks.json) exactly
reproduced both z129 parents' summaries and maxima, plus the complete sealed
y33 n512 physics result. The [diagnostic replay](diagnostic_tool_checks.json)
reproduced all 20 full-field and 54 fixed-support time metrics from the
[older three-time study](../20261107-geometric-time512/README.md), its whole
trace report, the older two-time increments and four explicit order/floor
checks. The field formula is extracted unchanged from that sealed input.
Replays and fault injections earn zero new simulation credit.

The [field report](three_time_fields.json) gives max-norm increments and
`log2(d01/d12)` for sheet phi/Fn/Fp, trap occupancy and bulk potential at
every saved node. It separately retains the original 54 observables and
normalizations on fixed 65x9x65 support. The inherited normalized floor 1e-8
marks unresolved orders. Original spatial gates are not temporal acceptance.
The prelaunch [baseline](baseline_two_time_fields.json) is reproduced exactly.

| Time (ps) | n128 to n256 bulk change (microV) | n256 to n512 bulk change (microV) | Bulk order | Trap order |
| --- | ---: | ---: | ---: | ---: |
| 20 | 6.227563 | 3.087299 | 1.012322 | 0.9974876 |
| 40 | 10.30499 | 5.104236 | 1.013577 | 0.9813948 |
| 60 | 6.617636 | 3.286576 | 1.009731 | 0.9837321 |

The unchanged [trace comparator](three_time_trace.json) measures both
increments on the same 384 coarse ending times and physical intervals.
BE currents are interval-matched, including gate edges; cumulative terminal
charges remain signed. Adjacent clock gates stay at 1e-24 s, while three-way
accumulated spread is reported separately. The parent comparison reproduces
the previous z129 trace exactly. Resolved decreasing counts below are
descriptive, with full nondecreasing or unresolved entries retained in JSON.

| Trace category | Metrics | Resolved | Resolved decreasing |
| --- | ---: | ---: | ---: |
| state_at_common_times | 12 | 12 | 12 |
| interval_average_currents_and_rates | 8 | 8 | 8 |
| conduction_at_common_ending_times | 2 | 2 | 2 |
| cumulative_current_and_rate_integrals | 8 | 8 | 8 |

## Measured components and remaining controls

The [observable inventory](observable_increment_inventory.json) aligns all
54 original observable/scaling entries. It lists the last z increment at
n256 and the last time increment on z129 on the same fixed support. For
bulk potential:

| Time (ps) | z121 to z129 at n256 (microV) | n256 to n512 on z129 (microV) |
| --- | ---: | ---: |
| 20 | 208.3525 | 3.087299 |
| 40 | 162.1001 | 5.104236 |
| 60 | 184.6139 | 3.286576 |

The z increment at n512 is unmeasured. These components are not summed or
treated as absolute solution-error bounds. A matched n512 control on another
z mesh, combined spatial controls and an explicit observable error budget
remain necessary for joint qualification. Local node counts do not define a
uniform global h ratio. No temporal acceptance threshold is introduced.

This study adds one pulse, 1536 steps and four full fields; the two parents
are inherited once. Solver and trace tests (245 and 25) are inherited by exact
hashes, with zero reruns. All owned numerical workers exited. Solver/native,
production, calibration and the protected 1078-file inventory are unchanged.
No release was published or deployed. General 2D logic/memory/material,
quantum-transport and full Sentaurus qualification remain open.

See [scope](temporal_diagnostics.json), [policy](policy.json),
[provenance](PROVENANCE.json), [reproduction](reproduction/README.md) and
[hashes](MANIFEST.json).
