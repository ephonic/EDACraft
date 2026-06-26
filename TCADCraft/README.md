# TCAD — 3D Quantum-Corrected Semiconductor Device Simulator

A Python-driven, extensible semiconductor device simulation framework with an
extended-precision C++ solver core. It targets nanoscale devices where quantum
confinement, electrostatic coupling, tunneling and self-heating matter.

```
┌─────────────────────────────────────────────────────────────┐
│  Python API  —  geometry, materials, mesh, sweep, visualize │
├─────────────────────────────────────────────────────────────┤
│  Cython bindings (zero-copy numpy)                          │
├─────────────────────────────────────────────────────────────┤
│  C++ core —  Poisson, drift-diffusion, DG, BTBT, FE, thermal│
└─────────────────────────────────────────────────────────────┘
```

## Features

- **3D finite-difference Poisson solver** on structured Cartesian grids with
cut-cell edge permittivity at material interfaces.
- **Drift–diffusion** with Scharfetter–Gummel discretization.
- **Adaptive Gummel iteration** with damping, limit-cycle detection and
potential freezing for robust high-bias convergence.
- **Newton–Raphson** full-coupled solver with line-search damping; can use
Gummel as a warm start.
- **Density Gradient (DG)** quantum correction for nanoscale confinement.
- **Band-to-band tunneling (BTBT)**: local Kane model and non-local WKB
path-integral for TFET / tunnel-diode simulation.
- **Ferroelectric polarization**: vector Landau–Khalatnikov model with
quasi-static hysteresis and transient dynamics for FeFET / NC-FET analysis.
- **Self-heating**: lattice heat equation `∇·(κ∇T) = −P` coupled to the
electrical solve.
- **Cryo-CMOS models**: temperature-dependent mobility, Fermi–Dirac statistics
and carrier freeze-out.
- **Device templates**: planar MOSFET, FinFET, GAA nanosheet, GAA high-k,
GAA FeFET, TFET, heterojunction TFET, BSPDN GAA, tunnel diode (NDR),
Dirac-source FET and PN junction.
- **Mesh generation**: structured Cartesian grids and Gmsh unstructured
tetrahedral meshes (FVM-ready).
- **Post-processing**: terminal current extraction, band-diagram cutlines,
TFET / NDR metrics, mechanism attribution and discovery metrics (`Ion`,
`Ioff`, `SS`, `Vth`, `DIBL`).
- **Device discovery tools**: evolvable device grammar, mutation operators and
NSGA-II-style search loop.
- **Visualization**: 2D slices, 1D cutlines and 3D isosurfaces with
matplotlib / PyVista.
- **Solver backends**: dense direct LU for small grids, optional PETSc direct
LU for grids ≥ 2,000 nodes.

## Installation

Requires Python ≥ 3.10, a C++17 compiler and numpy.

```bash
# Recommended: create a virtual environment first
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate

# Install with visualization and Gmsh support
pip install -e ".[viz,gmsh]"
```

The build uses Cython to compile `tcad/core/_bindings.pyx` together with the
C++ sources in `src/`. PETSc is optional: if `petsc.h` is found under
`/opt/homebrew/opt/petsc` or `$PETSC_DIR`, the PETSc backend is compiled in.
To force a build without PETSc:

```bash
TCAD_USE_PETSC=0 pip install -e .
```

On Apple Silicon with PETSc, the build expects GCC (`gcc-15`/`g++-15`) because
the PETSc C++ headers use GNU extensions.

## Quick Start

```python
import tcad
from tcad.viz.plotter import plot_mesh_slice

# Build a 50 nm planar MOSFET
dev = tcad.Device.mosfet(
    Lg=50e-9, tox=1.5e-9, tsi=15e-9, W=50e-9,
    Vg=0.7, Vd=0.5,
)

# Simulate with voltage ramping for robust convergence at high bias
sim, results = tcad.simulate_device(
    dev,
    resolution=(5e-9, 2.5e-9, 2.5e-9),  # (dx, dy, dz)
    quantum=False,
    max_iter=120,
    tol=1e-8,
    ramp_steps=3,
)

print(f"Converged={results['converged']}, iters={results['iterations']}")

# Visualize electron concentration
plot_mesh_slice(sim.mesh, field="n", axis="y", coord=50e-9)
```

## Usage Examples

### 1. Gate-voltage sweep (Id-Vg)

```python
import numpy as np
from tcad import Device, simulate_sweep

device = Device.mosfet(
    Lg=50e-9, tox=1.5e-9, tsi=15e-9, W=50e-9,
    Vg=0.0, Vd=0.1,
)

sim, results = simulate_sweep(
    device,
    sweep_contacts={"gate": np.linspace(0, 1.0, 21)},
    resolution=(5e-9, 2.5e-9, 2.5e-9),
    ramp_steps=3,
    max_iter=120,
    tol=1e-8,
)

for r in results:
    vg = r["_voltages"]["gate"]
    n_max = r["n"].max()
    print(f"Vg={vg:.2f}V  n_max={n_max:.3e}")
```

### 2. FinFET double-gate device

```python
from tcad import Device, simulate_device

dev = Device.finfet(
    Lg=30e-9, tox=1.5e-9, tsi=10e-9, Hfin=30e-9,
    Vg=0.7, Vd=0.1,
)

sim, results = simulate_device(
    dev,
    resolution=(5e-9, 2.5e-9, 5e-9),
    quantum=False,
    max_iter=120,
    tol=1e-8,
)
```

### 3. PN junction equilibrium

```python
from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device

dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
mesh = structured_mesh_from_device(dev, nx=21, ny=21, nz=21)

sim = Simulator(mesh, temperature=300.0)
sim.set_material_from_mesh()
sim.set_contact("p_contact", 0.0)
sim.set_contact("n_contact", 0.1)

results = sim.run(max_iter=50, tol=1e-8)
assert results["converged"]
```

### 4. TFET with non-local BTBT

```python
from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device

dev = Device.tfet(
    Lg=20e-9, Lsd=20e-9, t_sheet=5e-9, W_sheet=10e-9,
    Vg=0.0, Vd=0.3, Vs=0.0,
)

mesh = structured_mesh_from_device(dev, resolution=(100e-9, 100e-9, 100e-9))

sim = Simulator(mesh, temperature=300.0)
sim.set_material_from_mesh()
sim.set_contact("source", 0.0)
sim.set_contact("drain", 0.3)
sim.set_contact("gate", 0.0)

# Non-local WKB path-integral avoids overestimation at sharp junctions
sim.set_btbt(enabled=True, use_nonlocal=True)

results = sim.run(max_iter=80, tol=1e-8)
print(f"Converged={results['converged']}, n_max={results['n'].max():.3e}")
```

### 5. Self-heating simulation

```python
from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device

device = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
mesh = structured_mesh_from_device(device, nx=11, ny=11, nz=11)

sim = Simulator(mesh, temperature=300.0)
sim.set_material_from_mesh()
sim.set_contact("p_contact", voltage=0.0)
sim.set_contact("n_contact", voltage=0.1)

sim.set_thermal_coupling(enable=True, ambient_temperature=300.0)

results = sim.run(max_iter=50, tol=1e-6)
print(f"T_max = {results['temperature'].max():.3f} K")
```

### 6. Real terminal-current extraction

```python
import numpy as np
from tcad import Device, simulate_sweep
from tcad.postprocess import extract_transfer_characteristics_current

dev = Device.mosfet(Lg=50e-9, tox=1.5e-9, tsi=15e-9, W=50e-9,
                    Vg=0.0, Vd=0.1)

sim, sweep = simulate_sweep(
    dev,
    sweep_contacts={"gate": np.linspace(0, 1.0, 21)},
    resolution=(5e-9, 2.5e-9, 2.5e-9),
    ramp_steps=2, max_iter=120, tol=1e-8,
)

metrics = extract_transfer_characteristics_current(
    sim, sweep, drain_contact="drain"
)
print(metrics)
```

### 7. Device discovery / evolutionary search

```python
from tcad.search.evolution import evolve

result = evolve(
    seed_template="mosfet",
    population_size=12,
    generations=6,
    allow_mechanism_mutation=True,
)

for cand in result.pareto_front:
    print(cand.perf, cand.novelty, cand.trust)
```

See `examples/` for complete runnable scripts covering MOSFET, FinFET, PN
junction, TFET, BJT, adaptive mesh refinement, PETSc backend, DevSim
comparison and device evolution.

## Solver Physics

**Poisson equation**

```
∇ · (ε ∇φ) = -q (p - n + Nd - Na)
```

**Drift–diffusion (Scharfetter–Gummel)**

```
∇ · Jn = q R,   Jn = q μn n E + q Dn ∇n
∇ · Jp = -q R,  Jp = q μp p E - q Dp ∇p
```

**Thermal coupling**

```
P = σ |E|²          # Joule heating
∇ · (κ ∇T) = −P    # steady-state heat equation
```

**BTBT**

- Local Kane: `G = A · |E|^D · exp(-B / |E|)`
- Non-local WKB: `T = exp(-2 ∫ √(2m* (Ec(x) - Ev(x))) / ħ dx)`

**Density Gradient quantum correction**

```
n_quantum = n_classical · exp(-b_n · ∇²(√n)/√n / VT)
p_quantum = p_classical · exp(-b_p · ∇²(√p)/√p / VT)
```

## Project Structure

```
.
├── src/                  # C++ solver core
├── tcad/                 # Python package
│   ├── core/             # Cython bindings + solver type enum
│   ├── geometry/         # Device templates and geometric primitives
│   ├── material/         # Material library
│   ├── mesh/             # Structured / unstructured mesh generation
│   ├── postprocess/      # Current, bands, metrics, mechanism, trust
│   ├── search/           # Grammar, mutation, evolution
│   ├── knowledge/        # Design-law library
│   ├── solver/           # Unstructured FVM backend
│   └── viz/              # Plotting helpers
├── examples/             # Runnable device examples
├── setup.py              # Extension build script
├── pyproject.toml        # Package metadata
└── CMakeLists.txt        # Standalone C++ library build
```

## Optional Dependencies

| Extra | Install | Purpose |
|-------|---------|---------|
| `viz` | `pip install -e ".[viz]"` | PyVista / VTK 3D visualization |
| `gmsh` | `pip install -e ".[gmsh]"` | Unstructured tetrahedral meshing |
| `dev` | `pip install -e ".[dev]"` | pytest, black, mypy |

## License

MIT — see [LICENSE](LICENSE).
