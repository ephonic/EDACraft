# Matched x/time four-corner control

Two new full 60 ps MoS2 pulses at x69/y9/z113 complete a **two-x-grid by
two-time-step** matrix with sealed x65 controls. Both new trajectories pass
the unchanged independent physical and linear acceptance checks. The x65/69
meshes and n128/256 resolutions establish local increments; a two-mesh result
does not establish spatial order or the original three-mesh 54-metric verdict.

## Protocol and checks

Both new driver files have identical bytes. A reversible AST check proves that
only the x selector changes from `x_m` to `x_m_endpoint1` in the accepted x65
GEOMETRIC_ND driver. CLI steps per phase is 128 or 256 (dt 0.15625 or 0.078125 ps).
The representative isothermal MoS2 parameters, y9/z113 geometry, traps,
thermionic contacts and SI float128 native extension are unchanged. The linear
cache is explicitly cleared after the initial equilibrium solve. Four complete
fields are retained per pulse at 0/20/40/60 ps.

Each case has a predeclared 6000 s wall/CPU budget, 4 GiB peak RSS and 48 GiB
address space. Cases run serially with one numerical thread. Nonlinear 1e-12
and original row-scaled true linear max-norm 1e-14 limits are unchanged.

| New control | Whole-run time (s) | Peak RSS (MiB) | Maximum nonlinear residual |
| --- | ---: | ---: | ---: |
| geometric_x69_n128 | 485.152 | 637.00 | 9.85674e-13 |
| geometric_x69_n256 | 783.996 | 630.97 | 9.86924e-13 |

The [independent audit](independent_audit.json) adds
**1,661,534 physical and ledger checks** over 1152
new BE steps, two pulses and eight full fields. It reconstructs carrier
statistics and transport, traps, dielectric Poisson and flux, electrostatic
energy, contact charges and terminal currents. The x69 n128/n256 initial
states and initial linear diagnostics match bit for bit. Thirteen corruptions
are rejected independently on each new trajectory, including late-step ledger
and residual faults, wrong cadence, wrong geometry and truncated traces.

Before launch, [auditor replay](auditor_tool_checks.json) reproduced sealed
128/256 results and the original x69 MMD full physical summary and maxima.
The synthetic ND-label replay only checks the auditor; it earns zero new
physical credit. All four matrix trajectories use the current frozen candidate
and GEOMETRIC_ND. The older x69 MMD trajectory has a different source inventory
and is used only as a replay fixture, not as a matrix corner or same-source
numerical parity claim. [Diagnostic checks](diagnostic_tool_checks.json)
reproduce prior passing/failing spatial fixtures and interval trace diagnostics,
and check signed mixed increments analytically plus five malformed inputs.

## Signed interaction and temporal traces

The [interaction report](space_time_interaction.json) subtracts signed arrays
on exact nested 65x9x113 common support before taking max norms:

`[u(x69,dt/2)-u(x65,dt/2)] - [u(x69,dt)-u(x65,dt)]`.

It reports 20 field/phase metrics, including initial states. The largest
normalized mixed increment is **1.39145117e-06**; **14/20** metrics
exceed the inherited **1e-08** normalized analysis floor. This is a
resolution classification, not a new acceptance gate or a physical decoupling
proof. No error bound or joint space/time qualification is established.

| Time (ps) | Mixed bulk-potential increment (V) |
| --- | ---: |
| 20 | 2.34597887e-08 |
| 40 | 3.47862793e-08 |
| 60 | 2.39214375e-08 |

The [time trace report](time_trace_diagnostics.json) uses the unchanged
interval-matched comparator on both x grids. It aligns ending-time states,
BE interval currents and signed cumulative terminal charges, including gate
edges. The x65 comparison exactly reproduces the sealed y/time result.
Two time resolutions on x69 provide increments rather than temporal orders.

## Scope and reproduction

Only the two x69 pulses are new: 1152 BE steps and eight fields. Two x65
pulses are inherited once. Solver tests (245) and trace tests (25) are inherited
by unchanged hashes, with zero reruns. No solver source was changed. All owned
workers exited. Native, production, calibration and the protected 1078-file
original source inventory remain unchanged. No release was published.

Next extend matched controls to a third x mesh and z refinements, then construct
an explicit error budget. General 2D logic/memory/material qualification,
quantum transport and complete Sentaurus equivalence remain open.

See [matrix scope](matrix_audit.json), [frozen policy](policy.json),
[provenance](PROVENANCE.json), [reproduction](reproduction/README.md) and
[hashes](MANIFEST.json).
