# TCADCraft

TCADCraft is EDACraft's semiconductor device simulation package. It combines
a Python API, Cython bindings and a C++ numerical core with classical
drift–diffusion, density-gradient quantum corrections and scoped multiphysics
models.

**Release candidate: 0.3.0rc2 (2026-11-08).** This release adds optional
lower-fill sparse orderings, explicit linear-cache release and interval-aware
transient diagnostics to the graphene/MoS2 classical sheet solver. It includes
the independently audited refinement studies completed through November 8.
It is a scoped research release; full Sentaurus equivalence and complete 2D
logic/memory-device qualification remain open.

See [release notes](RELEASE_NOTES.md), [validation scope](docs/releases/0.3.0rc2/VALIDATION.md),
[installation verification](docs/releases/0.3.0rc2/RELEASE_VERIFICATION.json)
and the [handoff manual](handoff1108.md).

## Changes since 0.3.0rc1

- Optional `MMD_AT_PLUS_A` and `GEOMETRIC_ND` preconditioner orderings for the
  coupled reused-GMRES backend; `COLAMD` remains the default. Original true
  row-scaled residual, correction, refresh and transactional guards are retained.
- Explicit `clear_linear_cache()` API on `SheetTransient` drivers
  drops the retained factor reference without changing the accepted physical state.
- Interval-matched BE currents, signed cumulative charges, three-time observed
  orders and lower-memory loading of complete transient records.
- Complete 60 ps MoS2 refinement controls with unchanged original observable
  support and thresholds, preserving failed coarse-grid and resource trials.

| Evidence | Result and scope |
| --- | --- |
| [z/time matrix](docs/optimization/20261108-geometric-z-time512/README.md) | z113/121/129 at x83/y9, three dt: original 54/54 gates at each dt; observed bulk time orders about 1.01 |
| [Refined x/time matrix](docs/optimization/20261107-geometric-x83-time/README.md) | x69/75/83 at two dt: 54/54 at both; [coarser sequence](docs/optimization/20261107-geometric-x75-time/README.md) remains 52/54 |
| [y/time matrix](docs/optimization/20261107-geometric-y-time256/README.md) | Three y meshes at two dt: 54/54; mixed increments below the analysis floor do not prove decoupling |
| [Geometric ordering](docs/optimization/20261107-geometric-ordering/README.md) | Captured-system checks and 245 targeted development regressions |
| [Explicit cache release](docs/optimization/20261106-linear-cache-release/README.md) | State-preserving API, with timeout evidence retained |
| [Trace analysis](docs/optimization/20261106-trace-analysis/README.md) | Gate-edge interval-current and signed-integral checks |

These are scoped numerical controls, not absolute error bounds or combined
x/y/z qualification. Historical reports describe their status when sealed;
later follow-ups above do not rewrite their raw evidence.

## Capabilities and limits

| Area | Available implementation | Qualification boundary |
| --- | --- | --- |
| Bulk devices | Structured Cartesian and optional unstructured workflows; MOSFET, FinFET, GAA and other device templates | Templates are starting points; quantitative predictions require validated models and parameters |
| Classical transport | Poisson, electron/hole continuity, steady/transient APIs and multiple linear solvers | Physics combinations and recovery paths have scoped validation |
| Quantum corrections | Density-gradient corrections in supported bulk workflows | Not a general Schrödinger–Poisson or NEGF solver |
| 2D materials | Graphene Dirac and MoS₂ parabolic-band Fermi–Dirac sheet statistics; charge and quantum capacitance | Representative parameters, homogeneous bands, isothermal constant mobility |
| Sheet electrostatics | Local gate or Cartesian 3D dielectric coupling; finite mesh-aligned side electrodes | General geometry, material calibration and full spatial convergence remain open |
| Sheet contacts | Ideal/resistive edges, parabolic thermionic injection and graphene Dirac mode supply | Separate model assumptions; not arbitrary vertical/tunnelling interfaces |
| Sheet dynamics | Backward Euler storage, single-level traps, conduction/displacement currents and transactional rollback | Short pulse controls do not establish full memory operation or endurance |
| Other physics | Contact, thermal, trap, ferroelectric, leakage, tunnelling and impact-ionization modules | A module's presence does not validate every coupled configuration |

Sheet number density is in **m⁻²**, charge density in **C/m²**, sheet current
in **A/m**, and integrated terminal current in **A**. A bulk material template
with an effective thickness is not interchangeable with the dedicated sheet
solver.

## Install a release binary

A tested **Linux x86_64 / CPython 3.13** native wheel and a source archive are
available under [binaries/](binaries/README.md). The wheel uses SI constants and
GCC float128; it is host-built and is not manylinux-certified. Follow the
compatibility notes and checksum instructions before installation.

```bash
python -m pip install binaries/linux-x86_64/tcad-0.3.0rc2-cp313-cp313-linux_x86_64.whl
```

The wheel is built from a clean source distribution and installed outside
the source tree. Fresh targeted test counts, example checks and artifact hashes
are recorded in the [release verification report](docs/releases/0.3.0rc2/RELEASE_VERIFICATION.json).
This is separate from inherited numerical evidence and is not a full-suite claim.

## Install from source

Linux is the validated native build platform for this candidate. Use Python
3.10 or newer, a C++17 GCC toolchain with `libquadmath`, and the dependencies
in `pyproject.toml`. The default core uses GCC `__float128` with 113 mantissa
bits. Python/SciPy sheet solvers use float64 and do not inherit the native
core's arithmetic precision.

```bash
git clone https://github.com/ephonic/EDACraft.git
cd EDACraft/TCADCraft
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
TCAD_USE_PETSC=0 TCAD_USE_LAPACK=0 python -m pip install '.[dev]'
```

For development, use `python -m pip install -e '.[dev]'` with the same build
environment. Optional extras are `viz` (PyVista/VTK) and `gmsh`.
Native Windows builds are unsupported by the current setup script; use Linux
or WSL2. macOS needs an appropriate toolchain and is not covered by the Linux
binary verification.

The default constants profile is `si`. `TCAD_CONSTANTS_PROFILE=legacy-charge`
selects a separate build for bounded classical comparison, not a full
commercial-software physics preset. A loaded binary cannot change profile.
Inspect the installed extension with:

```python
import tcad
from tcad.core import native_precision, native_constants

print(tcad.__version__)
print(native_precision())
print(native_constants())
```

## Graphene / MoS₂ sheet example

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
    linear_solver='reused_gmres',
    linear_ordering='GEOMETRIC_ND',
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

For MoS₂ use `mos2_sheet(reference_eV=-0.9)` and a suitable contact model;
for example, replace the resistance with `thermionic_barrier_n_eV=0.12`.
These are demonstration inputs, not sample-calibrated parameters.

The default `schur` electrostatic backend retains limits of 1024 sheet and
100000 total nodes. Explicitly select `coupled` for a sparse full Newton
system; practical scale depends on factorization resources. Direct sparse
solves remain the default. Optional `reused_gmres` requires the true original
row-scaled max-norm bound `min(1e-14, 0.01*tolerance)`. Rejected transient
steps retain accepted state, time, drive and cache. Serialized solver restart
and concurrent calls on one driver are not supported.

See the [sheet API](docs/sheet_sparse_coupling.md). Runnable examples under
`examples/` include `sheet_dielectric_contacts.py`, `sheet_transient_dd.py` and
`sheet_trap_balance.py`.

## Validation status

The latest nine-corner z/time matrix contains complete 60 ps trajectories.
Its two fresh n512 controls add **3072 steps, 8 complete fields and 2,089,230
independent physical/ledger checks**; seven parent pulses are inherited once.
All three dt pass the original 54 spatial endpoint metrics. The three z meshes
show bulk-potential observed time orders of approximately 1.01; all 90 trace
metrics have resolved decreasing temporal increments. Interval-conduction
orders near 0.86 show why uniform first-order or asymptotic claims are premature.

**Global spatial and joint spacetime error bounds remain unqualified.** Local
contact refinements do not provide a uniform global h ratio. Combined x/y/z
controls and a physical observable error budget remain necessary. Failed coarse
x controls and original timeout/memory-budget outcomes are retained.

Real sample/contact calibration, complete logic and memory workflows,
Schrödinger–Poisson/NEGF transport and comprehensive commercial/experimental
acceptance remain open. Previously excluded real a/c calibration, independent
three-temperature measurements, 200 ps three-temperature commercial/native
profiles and general complex energy/entropy closure are separate research items.
See [validation scope](docs/releases/0.3.0rc2/VALIDATION.md) and the
[previous release baseline](docs/releases/0.3.0rc1/VALIDATION.md).

## Development and release checks

```bash
python scripts/release_check.py
python -m pytest tests/test_sheet_statistics.py tests/test_sheet_reused_gmres.py -q
python -m build
```

The metadata check without calibration arguments does not certify real
experimental calibration or whole-device convergence. Tests include optional,
slow and external-reference workflows; targeted passes are not full-suite
claims. Source distributions include C++/Cython sources, examples, tests and
compact documentation. Large raw validation archives, commercial executables
and host-specific development environments are not bundled.

## License

MIT; see [LICENSE](LICENSE).
