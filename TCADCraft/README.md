# TCADCraft

TCADCraft is EDACraft's semiconductor device simulation package. It combines
a Python API, Cython bindings and a C++ numerical core with classical
drift–diffusion, density-gradient quantum corrections and scoped multiphysics
models.

**Release candidate: 0.3.0rc1 (2026-11-05).** This release adds a dedicated
classical sheet model for graphene and MoS₂, sparse coupling to a 3D dielectric,
transient carrier/trap dynamics and stronger solver acceptance/recovery checks.
It is a research release with explicit model limits. Complete Sentaurus
equivalence and complete 2D logic/memory-device qualification are not claimed.

See [release notes](RELEASE_NOTES.md), [validation and open gaps](docs/releases/0.3.0rc1/VALIDATION.md)
and [numerical provenance](docs/releases/0.3.0rc1/validation_summary.json).

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
python -m pip install binaries/linux-x86_64/tcad-0.3.0rc1-cp313-cp313-linux_x86_64.whl
```

Clean-source build, separate wheel installation, the graphene/MoS2 examples
and installed-package targeted tests passed: **1055 passed, 0 skipped; zero failures/errors**. See the
[release verification report](docs/releases/0.3.0rc1/RELEASE_VERIFICATION.json).

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

The sealed MoS₂ fine-mesh comparison completed **two 60 ps trajectories** on
a 129×17×129 mesh: **768 dynamic steps, 8 complete fields and 6,769,086
independent physics checks**. SI and legacy-charge physical records agree
exactly. Separate local-z probes passed 1,336,524 field checks, but cover only
initialization and one BE step at each of two refinements per profile.

**Spatial convergence remains unqualified.** Fine-grid temporal and joint
spacetime bounds, real sample/contact calibration, complete logic/memory
workflows and dedicated quantum transport remain open. The historical 282
final-source affected regressions are inherited evidence, not a fresh
full-suite result. Release build/install checks are recorded separately.

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
