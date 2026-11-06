# Sparse dielectric coupling for classical sheet DD

`DielectricSheetDriftDiffusion(..., electrostatic_backend='coupled')` retains
the free dielectric potentials in the Newton system, alongside separate
sheet electrostatic potential, electron quasi-Fermi energy, and hole
quasi-Fermi energy. It constructs sparse Cartesian Poisson blocks and uses
SciPy sparse direct solves by default. It does not construct a dense sheet Schur map.

```python
import numpy as np
from tcad.material import graphene_sheet
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion
from tcad.solver.sheet_transient import SheetTransient

device = DielectricSheetDriftDiffusion(
    np.linspace(0, 200e-9, 33),
    np.linspace(0, 100e-9, 3),
    np.linspace(-10e-9, 10e-9, 17),
    graphene_sheet(),
    sheet_index=8,
    permittivity_F_m=5 * 8.8541878128e-12,
    contact_z_bounds_m=(-2.5e-9, 2.5e-9),
    electrostatic_backend='coupled',
    mobility_n_m2_Vs=0.02,
    mobility_p_m2_Vs=0.01,
    transport_scheme='diffusion_enhanced',
    contact_resistance_ohm_m=0.003,
)
run = SheetTransient(
    device, initial_drive={'top_gate_voltage_V': 0.005}, tolerance=1e-12,
)
result = run.step(
    dt_s=2e-12, top_gate_voltage_V=0.025, drain_voltage_V=0.004,
    tolerance=1e-12,
)
assert result['accepted']
```

For a MoS2 example, use `mos2_sheet(reference_eV=-0.9)` with suitable contact
parameters; `thermionic_barrier_n_eV=0.12` replaces the contact resistance.
The same material, sheet density units, contact conventions, doping, fixed
sheet charge, in-plane sheet permittivity and trap models apply to both
electrostatic backends. Cellwise positive dielectric permittivity and
mesh-aligned finite side electrodes are supported.

`electrostatic_backend='schur'` remains the default and retains the 1024 sheet
node / 100000 total node limits. `schur_rhs_block_size` applies only to that
backend. The coupled backend has no such fixed caps; sparse factorization
memory and runtime determine the practical mesh size. No automatic mesh
adaptation is provided.

For the coupled backend, `linear_solver='reused_gmres'` optionally retains
one full Newton Jacobian LU as a GMRES preconditioner across Newton iterations
and accepted `SheetTransient` steps. The direct solver remains the default.
The cache distinguishes steady and backward-Euler operators and the exact
`dt_s`. At the first transient step, or after a time-step change, the next
required linear solve builds a candidate LU for that storage operator;
subsequent steps with the same `dt_s` reuse it.
This avoids carrying a steady-state preconditioner through a transient run.
Every iterative solution must have a finite true residual in the original
row-scaled system no larger than `min(1e-14, 0.01*tolerance)`, and a successful
GMRES stop flag. Its initial L2 stopping target is `sqrt(number_of_rows)`
times this max-norm bound, so a large system's aggregate roundoff floor does
not itself cause rejection. The original row-scaled max norm is always
checked. If a valid L2 stop misses that max-norm bound, one correction solves
the actual residual equation with the unmultiplied absolute target; its stop
flag, residual and the corrected original residual must all pass.
Each GMRES call uses zero relative tolerance, restart 60 and at most
10 cycles. A failed solve rebuilds the LU once; a second failure raises
`FloatingPointError`. Factorization and other solver exceptions propagate.
The nonlinear tolerance and physical acceptance criteria remain unchanged.

Iterative results include `linear_solver_diagnostics`: solve, factorization,
iteration and refresh counts, the absolute linear target, and true-residual
attempt records. `invalidated_initial_factor` reports an operator-key change;
`reused_initial_factor` reports a compatible incoming cache. Initial harmonic
bulk solves are separate from these Newton
counters. The initial LU still requires sparse direct-factorization memory;
this option does not guarantee lower memory use or faster execution.
The optional `linear_ordering='MMD_AT_PLUS_A'` selects a different SuperLU
column ordering for this Newton preconditioner. `COLAMD` remains the default;
the alternative requires `linear_solver='reused_gmres'`. Harmonic bulk solves
and the direct/Schur backends retain their current behavior. Diagnostics report
`factor_ordering`, and a factor from another ordering is invalidated before
reuse. Ordering does not change the true residual gate, iteration limits,
single-refresh policy or transactional rollback.

Development sources also accept `linear_ordering='GEOMETRIC_ND'` with
`linear_solver='reused_gmres'` and `electrostatic_backend='coupled'`.
This constructs a deterministic nested-dissection permutation from the sheet
and free dielectric node coordinates, permutes both rows and columns, and
uses SuperLU `NATURAL` ordering on that permuted system. The returned solution
is mapped back before checking the original equations. The immutable
permutation is shared across device copies; the cache identity also includes
its contents. Harmonic initialization keeps its existing sparse solve.
See the [y33 matrix study](optimization/20261107-geometric-ordering/README.md)
for targeted tests, captured-system measurements and remaining device checks.
This option is unreleased and does not imply a completed finer-y trajectory.
The [same-ordering y probe study](optimization/20261107-geometric-probes/README.md)
adds independently audited y9/y17/y33 initial and first-BE probes, with 26/26
original prefix metrics passing. Complete finer-y pulses and joint qualification remain open.

On one captured 37,737-row phase-two system, the alternative reduced LU fill
and peak process RSS while satisfying the same `1e-14` true max-norm bound.
Fresh complete 60 ps controls are documented in the
[full-pulse follow-up](optimization/20261106-full-pulse/README.md).
Neither measurement guarantees the same savings on other grids.
To compare on the included fixture, run each ordering in a fresh process with
the same thread limits:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python benchmarks/sheet_linear_ordering.py --ordering COLAMD
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python benchmarks/sheet_linear_ordering.py --ordering MMD_AT_PLUS_A
```

`gmres_corrections` and each attempt's correction record distinguish residual
correction from a LU refresh. Unrecoverable residual failures attach the
attempt records as `linear_solver_attempts` on the exception.

A factor is shared read-only when copying a device or transient driver;
geometry arrays and state remain independently owned. A solve builds its own
candidate cache, and a transient step publishes it only after its ledger and
both private/public result copies succeed. Rejected steps and exceptions
retain the accepted cache, drive, time and history. The factor is an in-process
resource, not a serialized restart. Concurrent calls on the same driver are
not supported.

Results include the full `dielectric_phi_V`, integrated displacement fluxes,
dielectric field energy, gate reactions, and combined source/drain electrode
charges. The coupled backend reports `electrostatic_backend='coupled'` and
`dielectric_free_residual_scaled_linf`; the main residual also includes every
free bulk equation. A warm start can include a finite `dielectric_phi_V` array
with shape `(nz, ny, nx)`. If omitted, the initial bulk potential is obtained
from the sheet and boundary potentials by a sparse linear solve.

`SheetTransient` owns a deep copy of the device and accepted history. It uses
the accepted full bulk field when computing displacement currents, and only
commits a converged step. Failed steps retain the previous drive, time,
carrier densities, trap occupancy and full bulk potential. Returned fields
can be modified without changing the accepted history.

This is an isothermal, homogeneous-band, constant-mobility classical sheet
model. It does not solve a Schrödinger or NEGF problem, or establish complete
memory-device or Sentaurus equivalence. Later fine-grid full pulses completed,
but spatial-convergence gaps remain open. See the
[release validation record](releases/0.3.0rc1/VALIDATION.md).
