# Same-ordering y9/y17/y33 initial and first-BE probes

**All three fresh `GEOMETRIC_ND` device probes pass independent physical and
resource checks. The original initial/first-BE y sequence passes
26/26 metrics.** This is a bounded prefix study;
complete y33 and full-pulse y convergence remain open.

The preceding [matrix-only ordering update](../20261107-geometric-ordering/README.md)
introduced the opt-in ordering. This follow-up uses that exact tested source
through its public coupled sheet/transient APIs, without a matrix monkeypatch.
The [earlier MMD y33 timeout](../20261106-third-y-probe/README.md) stays preserved.

## Frozen experiment

The three cases use x65/z113 and uniform nested y9/y17/y33 coordinates, a
representative isothermal MoS2 sheet, traps, finite side electrodes and the
same 0.15625 ps backward-Euler step. Only the y selector and ordering keyword
change from the sealed driver; [reversible AST checks](driver_derivation.json)
verify those edits. All three use `GEOMETRIC_ND`, avoiding mixed-ordering
roundoff in the three-grid comparison.

Runs are serial and single-threaded, with 48 GiB address space. The predeclared
y9/y17/y33 wall/CPU limits are 900/1800/3600 s and process peak-RSS audit gates
are 6/6/32 GiB. The nonlinear `1e-12` and true original row-scaled linear
max-norm `1e-14` limits are unchanged.

| y nodes | Bulk nodes | Whole probe wall time (s) | Peak process RSS (MiB) | Maximum nonlinear residual |
| --- | ---: | ---: | ---: | ---: |
| 9 | 66105 | 31.88 | 604.59 | 3.31298e-15 |
| 17 | 124865 | 157.25 | 1827.31 | 2.24167e-15 |
| 33 | 242385 | 951.00 | 6251.39 | 1.43535e-15 |

Each probe includes initialization, an accepted initial field and one accepted
BE step with a complete field. These are single-run measurements on the
recorded host. They do not establish a general speedup or full-pulse cost.

## Independent acceptance

The three cases pass **2,595,769 independent
physical and ledger checks**, covering sheet carrier/trap equations,
dielectric Poisson/fluxes, contact charges, field energy and terminal currents.
Each rejects nine corruptions: trace charge, dt, linear residual, bulk field,
gate drive, x/y geometry, cache protocol and wrong ordering. Atomic field
exports and accepted-step linear journals match the final records.

The checker parameterizes only two expected ordering-label constants in the
sealed case guard. The reverse AST transformation is exact. Before launch,
the adapted checker reproduced the inherited MMD y17 verdict/check count and
physical maxima; a synthetic metadata-only ND relabel replay and nine faults
tested label handling. These replays receive zero new physics credit.
See [tool checks](auditor_tool_checks.json) and [independent audit](independent_audit.json).

The [original metric function](derived/inherited_metric_function.py) evaluates
the same 26 observables at 0 and 0.15625 ps on fixed 65x9x65 common nodes.
It retains normalized last-difference `<0.01` and increment-ratio `<0.7`
tests above the original `1e-8` roundoff cutoff. The dense common-mesh
projection also reports descriptive changes on 65x9x113 nodes.
Metric failures: None.
See [all metrics and field changes](spatial_diagnostics.json).

[MMD/ND control differences](ordering_control_differences.json) compare the
same initial/first-BE y9/y17 fields and terminal quantities against retained
MMD runs. They are descriptive, with no added acceptance gate or simulation
credit. The y33 MMD run has no accepted field, so no y33 ordering parity is claimed.

Numerical source is unchanged from the 245-test candidate; those tests are
inherited by exact source hashes and were not rerun. Native code, 1,078
protected original files, calibration and production identities were verified.
All owned workers have exited. No release, commercial run, native rebuild or
production deployment was performed.

## Remaining work and replay

This study contributes **3 new BE steps, 6 full fields and 0 complete pulses**.
It does not qualify the complete y33 trajectory, full-pulse y convergence,
fine-grid time or joint space/time convergence. The next stage is a full y33
pulse with consistent same-ordering full controls, retaining the original
all-step ledgers and convergence gates. General 2D logic/memory, calibrated
material/contact parameters, quantum transport and full Sentaurus equivalence
remain outside this prefix study.

Use the [replay instructions](reproduction/README.md), [frozen policy](policy.json),
[provenance](PROVENANCE.json) and [file hashes](MANIFEST.json).
