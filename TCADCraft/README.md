# TCAD — 3D Quantum-Corrected Semiconductor Device Simulator

A Python-driven 3D semiconductor device simulation framework with **extended-precision** C++ solvers, targeting nanoscale devices where quantum confinement and electrostatic coupling matter.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Python API (tcad/simulator.py)                             │
│  • Geometry modeling (Device, Region, Material)             │
│  • Mesh generation (Structured / Gmsh unstructured)         │
│  • Visualization (matplotlib / PyVista)                     │
├─────────────────────────────────────────────────────────────┤
│  Cython Bindings (tcad/core/_bindings.pyx)                  │
│  • Double-precision interface, memory-zero-copy numpy       │
├─────────────────────────────────────────────────────────────┤
│  C++ Solver Core (src/*.cpp) — long double / __float128     │
│  • Sparse matrix & direct / iterative linear solvers        │
│  • 3D Poisson solver (finite difference)                    │
│  • Density Gradient (DG) quantum correction                 │
│  • Gummel self-consistent drift-diffusion                   │
│  • Newton-Raphson full-coupled solver                       │
│  • BTBT tunneling (local Kane + non-local WKB)              │
│  • Ferroelectric: LK + Preisach + NLS models, leakage (PF/FN), imprint │
│  • PETSc backend (>2k nodes auto-switch to direct LU)       │
└─────────────────────────────────────────────────────────────┘
```

## Features

- **Extended precision** C++ core (`long double` on Apple Silicon / GCC-15; `__float128` on Linux x86_64 with GCC < 15)
- **Adaptive Gummel convergence** — smart limit-cycle detection freezes φ when Poisson↔continuity coupling oscillates, letting carriers converge reliably
- **Newton-Raphson full-coupled solver** — hybrid Gummel-then-Newton strategy for rapid quadratic convergence on strongly coupled problems
- **Voltage ramping** — progressive bias stepping for MOSFETs at high Vg/Vd
- **PETSc direct LU** — automatic switch to `KSPPREONLY+PCLU` for grids > 2,000 nodes
- **Density Gradient (DG)** quantum correction for nanoscale confinement
- **Self-consistent thermal coupling** — Joule self-heating via lattice heat equation `∇·(κ∇T) = −P`
- **3D Geometry DSL** — boxes, spheres, cylinders, extruded polygons
- **Structured Cartesian grids** (FDM) + **Gmsh tetrahedral** (FVM ready)
- **Device templates** — MOSFET, FinFET, GAA nanosheet, TFET, Heterojunction TFET, FeFET, High-k GAA, BSPDN GAA, Tunnel Diode (NDR), PN junction, **Dirac-Source FET**
- **Visualization** — 2D slices, 1D cutlines, 3D isosurfaces (PyVista)
- **Band-to-band tunneling (BTBT)** — local Kane's model and non-local WKB path-integral for TFET simulation
- **Ferroelectric polarization** - three models for NC-FET / FeFET:
  - **Landau-Khalatnikov** (vector 3-component P, per-component branch continuation + spinodal switching)
  - **Preisach** (classical scalar play-operator, parameterised directly by Ps/Ec)
  - **NLS** (Nucleation-Limited Switching, Merz-law, finite-slope S-shaped loop for wurtzite ferroelectrics like AlScN)
  - **Material-driven FE detection** (fe_alpha!=0, not dielectric-constant window) - correctly identifies AlScN (eps_r~15)
  - **Internal/imprint field** (E_bi offset for +/- loop asymmetry)
  - **Leakage current** (Poole-Frenkel + Fowler-Nordheim, 0V non-closure)
  - **AlScN material** (Ps=140 uC/cm^2, Ec=3.5 MV/cm) in the material library
- **Academic-style visualization** - serif fonts, inward ticks, thin axes; P-V/P-E loop, Id-Vg transfer, and PUND pulse plotters
- **Cryo-CMOS models** — temperature-dependent mobility (Arora, low-T), Fermi-Dirac statistics, carrier freeze-out
- **Spatial DOS engineering** — per-node effective density-of-states (`Nc`, `Nv`) and bandgap (`Eg`) for heterogeneous devices
- **Adaptive mesh refinement** — feature-based and solution-driven error markers with multi-round adaptive loop
- **TFET metrics extraction** — subthreshold swing, I_on/I_off, energy-per-switch, TFET vs MOSFET comparison

## Quick Start

```bash
# Build extension (requires GCC/Clang, PETSc optional)
python setup.py build_ext --inplace

# Or install
pip install -e ".[viz,gmsh]"
```

```python
import tcad
from tcad.viz.plotter import plot_mesh_slice

# Build a 50nm MOSFET
dev = tcad.Device.mosfet(Lg=50e-9, tox=1.5e-9, tsi=15e-9, W=50e-9,
                         Vg=0.7, Vd=0.5)

# Simulate with voltage ramping for robust high-bias convergence
sim, results = tcad.simulate_device(
    dev,
    resolution=(5e-9, 2.5e-9, 2.5e-9),  # (dx, dy, dz)
    quantum=False,
    max_iter=120,
    tol=1e-8,
    ramp_steps=3,  # gradual 0→target bias
)

print(f"Converged={results['converged']}, iters={results['iterations']}")

# Visualize electron concentration slice
fields = sim.to_mesh_fields()
plot_mesh_slice(sim.mesh, field="n", axis="y", coord=50e-9)
```

### High-bias MOSFET (fine grid)

```python
from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device

device = Device.mosfet(
    Lg=50e-9, tox=1.5e-9, tsi=15e-9, W=50e-9,
    Vg=1.0, Vd=0.5, Na_body=1e23, Nd_sd=1e26,
)

# Exact 21×21×22 fine grid (≈10k nodes)
mesh = structured_mesh_from_device(device, nx=21, ny=21, nz=22)

sim = Simulator(mesh, temperature=300.0)
sim.set_material_from_mesh()
for name, voltage in device.contacts.items():
    sim.set_contact(name, voltage)

# PETSc auto-engages for >2k nodes
results = sim.run(max_iter=120, tol=1e-8)
assert results['converged']
```

### FinFET double-gate device

```python
from tcad import Device, simulate_device

dev = Device.finfet(
    Lg=30e-9, tox=1.5e-9, tsi=10e-9, Hfin=30e-9,
    Vg=0.7, Vd=0.1,
)

sim, results = simulate_device(
    dev, resolution=(5e-9, 2.5e-9, 5e-9),
    quantum=False, max_iter=120, tol=1e-8,
)
# Visualization: see examples/finfet_simulation.py
```

### TFET with non-local BTBT tunneling

```python
from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device
from tcad.postprocess.tfet import extract_tfet_metrics

# Tunnel FET: p+ source → light p channel → n+ drain
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

# Enable non-local (path-integral WKB) BTBT — avoids
# overestimation at sharp p+/n+ junctions
sim.set_btbt(enabled=True, use_nonlocal=True)

results = sim.run(max_iter=80, tol=1e-8)
print(f"Converged={results['converged']}, n_max={results['n'].max():.3e}")
```

### Tunnel Diode (NDR device)

```python
from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device
from tcad.postprocess.ndr import extract_ndr_metrics, extract_btb_current

# Esaki tunnel diode: heavily doped p+/n+ junction
dev = Device.tunnel_diode(
    Lp=20e-9, Ln=20e-9, W=20e-9, H=20e-9,
    Na=5e20, Nd=5e20,
)

mesh = structured_mesh_from_device(dev, resolution=(5e-9, 5e-9, 5e-9))

sim = Simulator(mesh, temperature=300.0)
sim.set_material_from_mesh()
sim.set_contact("anode", 0.0)
sim.set_contact("cathode", 0.0)
sim.set_btbt(enabled=True, use_nonlocal=True)

# Sweep forward bias to find NDR region
import numpy as np
results = []
for v in np.linspace(0.0, 0.3, 16):
    if sim.results is None:
        sim.set_contact("cathode", v)
    else:
        sim.update_contact("cathode", v)
    r = sim.run(max_iter=80, tol=1e-8)
    r["_voltages"] = {"cathode": v}
    results.append(r)

metrics = extract_ndr_metrics(results)
print(f"PVR={metrics['PVR']:.1f}, Vp={metrics['Vp']:.3f}V, Vv={metrics['Vv']:.3f}V")
```

### Self-heating simulation (thermal coupling)

```python
from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device

device = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
mesh = structured_mesh_from_device(device, nx=11, ny=11, nz=11)

sim = Simulator(mesh, temperature=300.0)
sim.set_material_from_mesh()
sim.set_contact("p_contact", voltage=0.0)
sim.set_contact("n_contact", voltage=0.1)

# Enable self-heating (thermal conductivity defaults to Si ~150 W/m·K)
sim.set_thermal_coupling(enable=True, ambient_temperature=300.0)

results = sim.run(max_iter=50, tol=1e-6)
print(f"T_max = {results['temperature'].max():.3f} K")
```

### Gate-voltage sweep (Id-Vg)

```python
import numpy as np
from tcad import Device, simulate_sweep

device = Device.mosfet(Lg=50e-9, tox=1.5e-9, tsi=15e-9,
                       W=50e-9, Vg=0.0, Vd=0.1)

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

### Dirac-Source FET (steep-slope device)

```python
from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device

# DSFET: graphene p+ source / Si channel / Si n+ drain
# The graphene source has a low effective DOS (Nc=Nv=1e17 cm⁻³)
# that suppresses the thermal tail of carrier injection,
# enabling sub-60 mV/dec subthreshold swing.
dev = Device.dirac_source_fet(
    Lg=50e-9, Lsd=30e-9, t_sheet=10e-9, W_sheet=20e-9,
    Vg=0.5, Vd=0.1,
)

mesh = structured_mesh_from_device(dev, resolution=(20e-9, 10e-9, 10e-9))

sim = Simulator(mesh, temperature=300.0)
sim.set_material_from_mesh()

for name, (shape, voltage) in dev.contacts.items():
    sim.set_contact(name, voltage)

# DSFET requires more iterations due to graphene/Si heterojunction
results = sim.run(max_iter=120, tol=1e-8)
print(f"Converged={results['converged']}, n_max={results['n'].max():.3e}")
```

## Solver Physics

### Poisson Equation
```
∇ · (ε ∇φ) = -q (p - n + Nd - Na)
```

### Drift-Diffusion (Scharfetter-Gummel)
```
∇ · Jn = q R,   Jn = q μn n E + q Dn ∇n
∇ · Jp = -q R,   Jp = q μp p E - q Dp ∇p
```

Discretized with the **Scharfetter-Gummel** scheme on structured Cartesian grids.

**Gummel iteration** (default, robust):
1. **Poisson solve** — φ from fixed n, p
2. **Continuity solve** — n, p from fixed φ
3. **Damping** — φ log-cap + adaptive reduction on oscillation
4. **Stabilization** — φ frozen when a persistent limit-cycle is detected (MOSFET strong inversion)

**Newton-Raphson** (opt-in, fast):
Solves φ, n, p simultaneously via block-Jacobian with line-search damping. Uses Gummel to generate a robust initial guess, then Newton refines in 1–2 quadratic iterations. Ideal for high-injection and optically generated carrier profiles where Gummel↔Poisson coupling is strong.

### Thermal Coupling (Self-Heating)
```
P = σ |E|²          # Joule heating power density  [W/m³]
∇ · (κ ∇T) = −P    # Steady-state heat equation   [K]
```
where `σ = q(μₙn + μₚp)` is electrical conductivity and `κ` is lattice thermal conductivity (default 150 W/(m·K) for Si). Enabled via:
```python
sim.set_thermal_coupling(enable=True, ambient_temperature=300.0)
```
Contact nodes are automatically anchored to ambient temperature; the Poisson solver is reused for the heat equation with PETSc direct LU for numerical stability.

### Band-to-Band Tunneling (BTBT)

Two models are available:

**Local Kane's model** (default):
```
G_BTBT = A · |E|^D · exp(-B / |E|)
```
Simple and fast, but overestimates tunneling at sharp p+/n+ junctions since it
depends only on the local electric field magnitude.

**Non-local WKB path-integral** (recommended for TFET):
```
T = exp( -2 · ∫ √(2m*·(Ec(x) - Ev(x))) / ħ dx )
G_BTBT = pre_factor · T
```
Integrates the tunneling barrier along the source-channel path (x-axis) using
Simpson's rule. Accounts for the full barrier profile, not just the local field,
giving physically correct carrier densities at heterojunctions.

```python
sim.set_btbt(enabled=True, use_nonlocal=True)
```

### Density Gradient Quantum Correction
```
n_quantum = n_classical · exp( - b_n · ∇²(√n)/√n / VT )
p_quantum = p_classical · exp( - b_p · ∇²(√p)/√p / VT )
```

## Solver Backends

| Grid size | Default backend | Notes |
|-----------|----------------|-------|
| < 2,000 | Dense direct LU (Eigen) | Fast for small 3D / 1D–2D |
| ≥ 2,000 | PETSc `KSPPREONLY+PCLU` | Direct LU via MUMPS/SuperLU |
| > 50,000 | PETSc iterative (configurable) | BiCGSTAB/GMRES + AMG |

Switch manually:
```python
from tcad.core import SolverType
sim.set_solver_type(poisson_solver=SolverType.PETSC,
                    continuity_solver=SolverType.PETSC)
```

## Testing

```bash
python -m pytest tests/ -q
# 160+ tests covering PN junction equilibrium, MOSFET bias sweeps,
# devsim comparison, Newton validation, SRH/optical generation,
# thermal coupling self-heating, mesh correctness (adaptive + solution-driven),
# TFET device templates, local/non-local BTBT, TFET vs MOSFET comparison,
# and NDR tunnel diode physics.
```

## Progress & Roadmap

### Completed (as of 2026-06-18)

#### Core Solver Physics
| Module | Status | Description |
|--------|--------|-------------|
| Poisson solver | Done | 3D FDM with edge permittivity (cut-cell), PETSc direct LU >2k nodes |
| Drift-Diffusion (Gummel) | Done | Scharfetter-Gummel discretization, adaptive convergence, phi freezing |
| Newton-Raphson | Done | Full-coupled solver with line-search damping, Gummel warm-start |
| Density Gradient quantum correction | Done | Bohm-potential for nanoscale confinement |
| BTBT — local Kane | Done | `G = A·|E|^D·exp(-B/|E|)` |
| BTBT — non-local WKB | Done | Path-integral tunneling along source-channel direction |
| Ferroelectric LK model | Done | Vector 3-component P (Px,Py,Pz), isotropic component-wise Landau solve, quasi-static hysteresis (±Ps branch memory via P persistence across bias) + transient |
| Cryo-CMOS models | Done | Temperature-dependent mobility, Fermi-Dirac statistics, freeze-out |
| Thermal coupling | Done | Joule self-heating via `∇·(κ∇T) = −P` |
| Transient solver | Done | Backward Euler time stepping, NC-FET vs FeFET classification |

#### Ferroelectric Hysteresis (Loop A)
| Step | Status | Description |
|------|--------|-------------|
| A0 — transient BE redo | Done | Backward-Euler transient solver audit/fix (audit §17); reliable NC-FET/FeFET transient classification |
| A1-A3 — signed P + hysteresis | Done | Signed-scalar P with quasi-static LK hysteresis: ±Ps branch memory, path-dependent Vg-sweep loop (audit §18) |
| A4 — vector P (Px,Py,Pz) | Done | 3-component vector polarization: isotropic component-wise Landau solve, vector ∇·P = dPx/dx+dPy/dy+dPz/dz, 1-D scalar behavior recovered as the Px-only special case (audit §19) |
| A5 — documentation | Done | audit0618.md §19 (design/change-list/test/limits) |

Truth-chain tests: single-node signed-LK hysteresis loop, C++ end-to-end Vg-sweep on a pure FE slab (P flips at ±Vmax, ±Pr at Vg=0, loop closes), and 2-D vector-decoupling (simultaneous Px & Py driven, impossible under the prior scalar model).

#### Device Templates
| Device | Status | Description |
|--------|--------|-------------|
| MOSFET (planar) | Done | Standard planar NMOS/PMOS |
| FinFET | Done | Double-gate FinFET |
| GAA nanosheet | Done | Gate-all-around nanosheet |
| GAA High-k | Done | GAA with HfO2 gate stack |
| GAA FeFET | Done | Ferroelectric GAA (HfZrO gate stack) |
| TFET | Done | Tunnel FET with BTBT, sub-60mV/dec |
| Heterojunction TFET | Done | SiGe source TFET with reduced bandgap |
| BSPDN GAA | Done | Backside power delivery network |
| **Tunnel Diode (NDR)** | Done | Esaki diode with negative differential resistance |
| **Dirac-Source FET** | Done | Graphene-source steep-slope device with spatial DOS engineering |
| PN junction | Done | Simple 1D-like p-n junction |

#### Mesh & Postprocessing
| Module | Status | Description |
|--------|--------|-------------|
| Structured mesh generator | Done | Cartesian grid from device geometry |
| Adaptive mesh refinement | Done | Feature-based + solution-driven, multi-round adaptive loop |
| TFET metrics | Done | SS, V_on, I_on/I_off, energy-per-switch, TFET vs MOSFET comparison |
| NDR metrics | Done | Peak/valley current, PVR, NDR region bounds, I-V plotting |

#### Material Library
| Material | Status | Description |
|----------|--------|-------------|
| Silicon | Done | Crystalline Si baseline |
| SiO2 | Done | Gate dielectric |
| HfO2 | Done | High-k dielectric (kappa=20-30) |
| HfZrO | Done | Ferroelectric with Landau coefficients |
| SiGe | Done | Si1-xGex alloy (Vegard's law) |
| Al2O3 | Done | Interfacial layer |
| Graphene | Done | Dirac-cone source with suppressed DOS (Nc=Nv=1e17 cm⁻³) |
| MoS₂ | Done | TMDC channel material (Eg=1.8 eV) |
| TiN / W | Done | Metal gate / contact workfunctions |

#### Test Coverage
| Category | Count | Status |
|----------|-------|--------|
| PN junction / MOSFET | ~40 | Passing |
| Newton / DevSim comparison | ~10 | Passing |
| SRH / optical / thermal | ~10 | Passing |
| Adaptive mesh refinement | ~8 | Passing |
| TFET templates + DD | ~15 | Passing |
| TFET vs MOSFET comparison | ~3 | Passing |
| Non-local BTBT validation | ~3 | Passing |
| **NDR tunnel diode** | **~11** | **Passing** |
| **Ferroelectric hysteresis (Loop A)** | **11** | **Passing** — signed-LK loop, C++ Vg-sweep, 2-D vector decoupling |
| **Bands / mechanism / truth-chain (M5)** | **50** | **Passing** — `test_bands.py` (16), `test_mechanism.py` (22), `test_trust_gate.py` (12) |
| **Design-law library + grammar/mutation/evolution (M6 / Loop C+D)** | **102** | **Passing** — `test_grammar.py` (12), `test_mutation.py` (14), `test_evolution.py` (37), `test_discovery_metrics.py` (9), `test_laws.py` (30) |
| **Log-space Newton solver (M6b)** | **7** | **Passing** — `test_log_space_solver.py` |
| **Contact current extractor 1D/2D (M6c)** | **12** | **Passing** — `test_contact_current.py` (7), `test_contact_current_2d.py` (5) |
| **DevSim 2D PN-junction bias comparison (M6c-3)** | **4** | **Passing** — `TestPNJunction2dBias` in `test_devsim_comparison.py` (sign + KCL + magnitude + bias trend) |
| Pre-existing failures | 1 xfail | DG-related (known, tracked) |

### Planned
| Module | Priority | Description |
|--------|----------|-------------|
| Impact Ionization MOS (I-MOS) | Next | Avalanche multiplication for sub-60mV/dec switching |
| Spin FET (Datta-Das) | Future | Spin-injection and precession-based switching |
| First-principles Dirac-Cone | Future | Exact DOS(E) ~ |E| instead of engineering approximation |
| GAAFET multi-nanosheet | Future | Stacked nanosheets for higher drive current |
| IR drop analysis | Future | BSPDN power delivery network voltage drop |
| Hysteresis analysis | In progress | FeFET memory window extraction, NC-FET classification — hysteresis *physics* done (Loop A); metrics extraction is Loop B (see plan0618.md) |

### Evolution Research Program (Loop B/C/D)
A TCAD tool-device co-evolution program toward new-principle device discovery. **Loop A** (ferroelectric LK + hysteresis) is complete; **Loop B/C/D** are defined in [`plan0618.md`](plan0618.md), aligned to the four research mainlines in [`device_evole.md`](device_evole.md):

| Loop | Mainline | Goal | Status |
|------|----------|------|--------|
| A | (audit FE workstream) | Vector ferroelectric LK + hysteresis | ✅ Done (A0–A5) |
| B | Multi-physics TCAD evaluation | Multi-fidelity sim pipeline + logic/storage/novelty metrics | 🟡 In progress — discovery metrics (`tcad/postprocess/discovery.py`) + log-space Newton (M6b) shipped |
| C | Mechanism-guided evolutionary search | Evolvable device grammar + NSGA-II + surrogate | 🟡 In progress — grammar / mutation / evolution operators landed under `tcad/search/` (M6) |
| D | Design-law extraction | Band/field/mechanism analysis + design-law library | 🟡 In progress — bands + mechanism + trust-chain (M5) and design-law library under `tcad/knowledge/` (M6) shipped; DevSim 1D + 2D current validation harness (M6c) operational |

## Recent Progress (M5 – M8/A·B·C档, June–July 2026)

The Loop B/C/D research program is being delivered in numbered milestones (`plan0619.md`).
The most recent milestones are now landed and verified:

### M5 — Band-structure + mechanism attribution + truth-chain
- `tcad/postprocess/bands.py` — extract `Ec(x)`, `Ev(x)`, `Ef_n(x)`, `Ef_p(x)` cutlines from solver state, with the corrected coordinate-sorted edge ordering (audit §19).
- `tcad/postprocess/mechanism.py` — classifies the dominant transport mechanism per node (drift, diffusion, BTBT, thermionic) from the local field/concentration ratio.
- `tcad/postprocess/trust.py` — physics truth-chain: every reported metric carries a provenance gate (mesh ✓ / solver ✓ / physics-law ✓) so that downstream evolution loops only consume validated artefacts.
- Tests: `test_bands.py`, `test_mechanism.py`, `test_trust_gate.py` — all green.

### M6 — Loop C/D core: design-law library, grammar, mutation, evolution
- `tcad/knowledge/` — versioned design-law library (D4); each law is encoded with applicability domain + provenance link to the validating truth-chain artefact.
- `tcad/search/{grammar,mutation,evolution,...}` — evolvable device grammar (terminal symbols = template parts; production rules = topology mutations) and NSGA-II-style mutation/recombination (Loop C).
- `tcad/postprocess/discovery.py` — discovery metrics (logic / storage / novelty) consumed by Loop B's multi-fidelity evaluator.
- Tests: `test_grammar.py`, `test_mutation.py`, `test_evolution.py`, `test_discovery_metrics.py`, `test_laws.py` — all green.

### M6b — Log-space Newton solver
- `n, p` solved in `log n`, `log p` space with strictly positive iterates by construction; eliminates the negative-density blow-ups that otherwise dominate at high reverse-bias.
- Tests: `test_log_space_solver.py` — all green.

### M6c — Contact-current extractor + DevSim cross-validation
- `tcad/postprocess/current.py::contact_current_1d / contact_current_2d` — integrate `Jn + Jp` over a contact face using the C++ solver's edge-flux outputs (`Jn_x, Jp_x, Jn_z, Jp_z`) at full `__float128` precision (audit §20).
- Audit §19 (coordinate ordering bug) and audit §20 (`__float128` solver-output edge fluxes) are now closed and have tests pinning the fix.
- DevSim cross-validation harness:
  - `tests/test_contact_current.py` (1D) and `tests/test_contact_current_2d.py` (2D) — 12/12 passing.
  - `tests/test_devsim_comparison.py::TestPNJunction2dBias` (M6c-3, 4/4 passing) — **2D PN-junction terminal current vs. DevSim 2D**, validating sign, KCL between p- and n-contact, magnitude (`|log10(I_tcad / I_devsim)| < 1`), and forward-bias monotonicity over `Vbias ∈ {0.2, 0.3, 0.4} V`.
  - Full suite: `tests/test_devsim_comparison.py` — 21/21 passing in 17.6 s.

### Test snapshot
```
tests/test_devsim_comparison.py     21 passed   (17.6 s)
tests/test_contact_current.py        N passed   (part of 12/12 with 2D)
tests/test_contact_current_2d.py     M passed   (part of 12/12 with 1D)
                                  total 12/12   (223 s)
```

### M7a — Avalanche impact ionization + ferroelectric-coupling fix (audit §21)

**Ferroelectric self-consistency fix (user-reported HZO non-switching / missing
memory window).** Root cause confirmed in code: the Gummel↔Newton self-consistent
loop did **not** fully couple polarization to carriers:
1. **φ-freeze froze P too** — the polarization update lived inside the
   `if (!phi_frozen)` block of the Gummel loop, so once the limit-cycle
   stabilizer froze φ, P was pinned to its value at the freeze instant and could
   no longer follow the ramped gate → no switching, no hysteresis, no memory
   window. **Fix:** P now refreshes every iteration against the current φ.
   (`src/gummel_solver.cpp`)
2. **Newton path dropped ferroelectric entirely** — the Newton Poisson residual
   (`newton_solver.cpp`) had no `-div(P)` bound-charge term, so any solve routed
   through Newton (`use_newton=True`, or `solve_transient`) silently disabled
   ferroelectric coupling. **Fix:** Newton now carries `-div(P)` exactly as
   `PoissonSolver::assemble` does, with P+mask injected from `DeviceSimulator`.
   (`src/newton_solver.cpp`, `src/device_simulator.cpp`)
3. **Spinodal switching re-seed** — when the drive field opposes P and exceeds
   the coercive field `Ec = (2|α|/3)·√(-α/3β)`, the L-K Newton (started from the
   old well) converged back to the local minimum instead of crossing the barrier
   → sporadic non-switching. **Fix:** re-seed to the opposite signed well
   minimum past the spinodal. (`src/poisson_solver.cpp`)

Tests (`tests/test_fe_coupling_and_ionization.py`, all green): Newton-path
hysteresis (P switches + remanence), Gummel/Newton remanence-sign agreement,
single-step spinodal switching.

**Avalanche impact ionization (Chynoweth).** New module mirroring the BTBT
add-on (four-layer binding: `Simulator.set_impact_ionization` → Cython →
`DeviceSimulatorDouble` → `DeviceSimulator`):
- `ImpactIonizationParams { A_n, B_n, A_p, B_p; E_floor }` (SI units, silicon
  defaults pre-converted from 1/cm & V/cm literature).
- `G_ii = (alpha_n·|Jn| + alpha_p·|Jp|)/q` in **edge form** (per-edge SG current
  density, same convention as `compute_edge_currents`, audit §20), injected into
  both continuity equations in the Gummel and Newton paths.
- Coefficient law `alpha(E) = A·exp(-B/|E|)` with a field-floor guard (1e5 V/m).
- Tests: Chynoweth α(E) curve unit test, field-floor onset, four-layer setter
  round-trip — all passing.
- **Known limitation:** a converged avalanche I-V requires a fully-coupled
  Newton Jacobian carrying `dG_ii/dn` (the II source is strong positive
  feedback); the alternating-sweep Gummel path converges only while II stays
  sub-critical. Full coupled-Jacobian avalanche is a follow-on task (as in
  commercial tools).

### Test snapshot (M7a)
```
tests/test_fe_coupling_and_ionization.py   6 passed, 1 skipped
tests/test_numerical_validation.py        32 passed, 1 xfailed
tests/test_devsim_comparison.py           21 passed
tests/test_simulator.py                   all pass
```

### M7b — Dielectric (gate-oxide) breakdown (audit §22)

When the oxide electric field exceeds the material breakdown field `E_bd`
(SiO2 ≈ 1.2e9 V/m, HfO2/HfZrO ≈ 6e8 V/m), the node is flagged *soft-broken*
and a leakage conductance `sigma_bd` is added to its Poisson diagonal on
subsequent solves — locally relaxing `phi` toward 0 (a soft short) so a gate
leak develops. The breakdown is **irreversible** (the conductive filament
persists across bias points), mirroring the `fe_polarization_` persistence
mechanism.

- `Material.E_bd` field added (defaults 0 = no breakdown); `sio2()`/`hfo2()`/
  `hfzro()` populated. `Device.sample_on_grid` emits a per-node `E_bd` mesh
  field.
- `PoissonSolver::set_breakdown_state(bd_state, sigma_bd)` + leakage term in
  `assemble()`; `GummelSolver` forwards it; `DeviceSimulator` holds the
  authoritative `bd_state_` (persisted across `solve()`), detects `|E|>E_bd`
  after `compute_electric_field`, and flips nodes 0→1.
- Python: `Simulator.set_breakdown(enabled, sigma_bd)`; inspect via
  `sim._sim.breakdown_state()`.
- Tests (`tests/test_dielectric_breakdown.py`, all green): oxide field tracks
  `Vg/tox`, state flips above `E_bd`, **irreversibility** (state survives bias
  reduction), sub-threshold guard (no false trigger below `E_bd`).

### Test snapshot (M7b)
```
tests/test_dielectric_breakdown.py   4 passed
regression (devsim + geometry + FE + breakdown)  53 passed, 1 skipped
```

### M7c — Classical scalar Preisach model (audit §23, conclusion ①)

Closes the conclusion-① gap (codebase had **only** L-K; no Preisach). Adds a
second ferroelectric model selectable at runtime:

- `enum class FerroelectricModel { LANDAU_KHALATNIKOV=0, PREISACH=1 }`
  (mirrors the `MobilityModelType` int→enum pattern).
- **Preisach** realised as the classical **play-operator** (moving model): each
  node carries an internal "play" value `w` that tracks the field `E` but lags
  by the coercive half-width `Ec`; output `P = Ps·tanh((E−w)/Ec)` saturates at
  ±`Ps`. This gives a natural memory (`w`) and a true hysteresis loop,
  parameterised **directly by `Ps` and `Ec`** — sidestepping the L-K α/β
  dimensional ambiguity entirely (conclusion ①'s root cause).
- The play state `fe_play_state_` is persisted across `solve()` (same
  injection/read-back mechanism as `fe_polarization_`), so a Vg sweep produces
  path-dependent memory.
- Python: `Simulator.set_ferroelectric(model="landau_khalatnikov"|"preisach",
  Ps=..., Ec=...)` and `set_ferroelectric_model(model, Ps, Ec)`.
- The L-K `set_ferroelectric(alpha, beta)` path is unchanged (fully backward
  compatible; default model is L-K).
- Tests (`tests/test_preisach_model.py`, all green): bipolar-loop hysteresis
  with memory window, off-axis Py/Pz=0 in 1-D field, output bounded by `Ps`,
  both models selectable and bounded.

**With M7a–M7c the three reported conclusions are now addressed:**
- ① Preisach available (M7c) ✓
- ② L-K hysteresis robust on both Gummel & Newton paths (M7a FE-coupling fix) ✓
- ③ breakdown — avalanche impact ionization (M7a) + gate-oxide dielectric
  breakdown (M7b) ✓

### Test snapshot (M7c)
```
tests/test_preisach_model.py   4 passed
regression (numval + FE + preisach + breakdown + devsim)  67 passed, 1 skipped, 1 xfailed
```

### M8/A档 — Analytic-limit validation + 2 bug fixes

Validates the M7 modules against their **known analytic properties** (mathematical
identities of the models, no external reference) — catching "the equation was
written wrong" bugs that qualitative tests miss. Surfaced and fixed **2 real
bugs**:

**Bug 1 — Preisach saturation cap** (`poisson_solver.cpp`): `Escale=Ec` was
hardcoded, so on a monotonic ramp `arg=(E-w)/Ec` was pinned at 1 and `|P|`
capped at `tanh(1)·Ps≈0.76·Ps` — it could never reach the named saturation `Ps`.
**Fix (A档):** decoupled `Escale` as an independent parameter
(`set_ferroelectric_preisach(Ps, Ec, Escale)`); `Escale=0` keeps legacy
behaviour, `Escale<Ec` (e.g. `Ec/3`) lets `|P|→Ps`.

**Bug 2 — breakdown dimensional inconsistency** (`poisson_solver.cpp`):
`sigma_bd` was documented `[S/m]` but added to the Poisson diagonal `[F/m³]` —
off by ~1e9×. **Fix (A档):** redefined `sigma_bd` as `[F/m³]` (effective added
permittivity-density, same units as `eps/dx²`), making the addition
dimensionally self-consistent. Default updated `1e-4→1e-2`.

**Analytic-limit tests** (`tests/test_analytic_limits.py`, 16 passed):
- L-K: Newton-solved P vs Cardano closed-form root (rel-err <1e-6 across
  0.01Ec…5Ec…1e9), linear response about the well, spinodal identity.
- Preisach: `Ps→0→P=0`, `Escale<Ec` lets `|P|→Ps`, legacy cap pinned,
  memory-window (opposite-branch remanence), Escale monotonicity.
- Breakdown: `sigma_bd→∞` hard-short (phi→0), `sigma_bd→0` no-leak,
  `E_bd→∞` never-break, dimensional-response monotonic.
- Impact ionization: `E→0→α=0`, `E→∞→α=A` saturation, monotonicity.
- Newton↔Gummel quantitative agreement on FE P (audit §21 regression guard).

### Test snapshot (A档)
```
tests/test_analytic_limits.py        16 passed
tests/test_numerical_validation.py   32 passed, 1 xfailed  (L-K unaffected)
regression (preisach+FE+breakdown+devsim+coords)  61 passed, 1 skipped
```

### B档 — Mesh-generation correctness + MMS grid-convergence

Validates the mesh/discretization foundation. Surfaced and fixed **2 more real
bugs**:

**Bug 3 — adaptive_refiner i,j,k scramble** (`adaptive_refiner.py`): three sites
used plain `.reshape(nx,ny,nz)` (C-order, k fastest) on node-ordered flat
arrays instead of `grid.to_3d()` (i fastest). In 3D this scrambled material
interfaces — an x-direction interface was flagged for y/z refinement. Fixed
all three to `to_3d()`.
**Bug 4 — silent zero-contact-node** (`simulator.py`): a contact thinner than
one cell left the Dirichlet BC map empty and the C++ solver silently applied no
BC (the devsim-2D failure mode). Now raises `ValueError`. Added `StructuredGrid`
bbox validation (`xmin < xmax` strict).

- Mesh-correctness tests (`tests/test_mesh_correctness.py`, 12): `to_3d`/`index`
  consistency, `to_3d ≠ plain reshape` (pins Bug 3), degenerate grids, bbox
  validation, cut-cell harmonic mean at Si/SiO2, adaptive-refiner axis
  correctness (Bug 3 regression guard), zero-contact guard (Bug 4).
- MMS grid-convergence (`tests/test_mms_convergence.py`): reusable
  `richardson_rate` helper; Poisson sine-box 2nd-order Richardson; FE `-div(P)`
  convergence; 1D driven-boundary convergence.

### C档 — freeze_phi exposure + pure-Poisson RHS-driven MMS

- **Exposed `freeze_phi`/`freeze_n`/`freeze_p`** to Python (4-layer binding +
  `Simulator.set_freeze_phi/n/p`). These pin a Newton block to its current
  value, enabling an isolated continuity solve (flat band kills the drift term)
  — the precondition for a DD-continuity MMS.
- **Pure Poisson RHS-driven MMS** (strongest stencil check): manufacture
  `phi_exact = A·sin(kx)`, inject the analytic Laplacian `Nd-Na = eps·k²·A/q·sin`
  as a doping source, pin boundaries to `phi_exact`, and compare **directly to
  the analytic solution** (not just Richardson self-convergence). Verified
  `|phi_num − phi_exact|` shrinks at **rate ≈ 2.0** across nx=21/41/81.
- DD-continuity MMS explored: `freeze_phi` is Newton-only, but `solve()` runs a
  Gummel warm-up first (which doesn't freeze phi), so a clean isolated-
  continuity solve needs a pure-continuity solve mode — documented as follow-on.
  The Poisson RHS-driven MMS is a strong substitute (same 2nd-order stencil).

### Test snapshot (B/C档)
```
tests/test_mesh_correctness.py    12 passed
tests/test_mms_convergence.py      6 passed   (3 B档 + Poisson RHS + freeze binding + ...)
regression (mesh+mms+analytic+numval)  65 passed, 1 xfailed
```

## Ferroelectric Device Improvements (P1–P4, July 2026)

Based on experimental feedback testing HZO capacitors, AlScN capacitors (PUND),
and AlScN+MoS₂ FeFETs, four phases of fixes were implemented:

### P1 - Configuration Bugs & Parameter Chain

- **Material-driven FE detection**: replaced the hard-coded `epsilon_r ∈ [25,50]`
  window with `fe_alpha ≠ 0` material metadata. AlScN (ε_r ≈ 15) was silently
  excluded by the old window — now correctly identified as ferroelectric.
- **Parameter unification**: solver defaults aligned to material library
  (α = −5×10⁸, β = 1.5×10¹⁰). Material `fe_alpha`/`fe_beta`/`fe_ps`/`fe_ec`
  are now written to mesh fields and auto-read by `set_ferroelectric()`.
- **AlScN material**: `alscn()` in the material library with Ps = 1.4 C/m²
  (140 μC/cm²), Ec = 3.5 MV/cm — meeting the 130–150 μC/cm² target.

### P2 - Leakage Current & Internal Field

- **Internal/imprint field** (P2.1): `E_eff = E − E_bi` breaks ±loop symmetry.
  `set_ferroelectric_builtin_field(E_bi)` — 0 gives a symmetric loop.
- **PF/FN leakage** (P2.2): Poole-Frenkel and Fowler-Nordheim emission models
  add a field-dependent conductance to the Poisson diagonal of leaky nodes,
  normalised to `eps/dx²`. Reproduces the experimentally observed **0V
  non-closure** of the P-V loop and off-state gate leakage.
  `set_leakage(enabled, pf_C, pf_B, ..., fn_C, fn_B, ...)`.

### P3 - NLS Switching Model

- **Nucleation-Limited Switching** (`model="nls"`): Merz's law
  τ(E) = τ₀·exp(E₀/|E|). In quasi-static operation the polarization relaxes
  toward ±Ps by a fractional amount per bias step, producing a **finite-slope
  S-shaped loop** instead of an instantaneous vertical jump — fixing the
  "switching is completely vertical" failure for AlScN FeFETs.
  `set_ferroelectric_model("nls", Ps, Ec, nls_tau0, nls_E0, nls_dt)`.

### P4 - Academic Visualization & Loop Drivers

- **Academic style** (`tcad/viz/style.py`): `set_academic_style()` /
  `science()` context manager — serif fonts, inward ticks, thin axes.
- **Device-characteristic plotters** (`tcad/viz/plotter.py`):
  `plot_pv_loop()`, `plot_pe_loop()`, `plot_transfer()`, `plot_pund()`.
- **Loop drivers** (`tcad/postprocess/fe_loops.py`):
  `run_pv_sweep()`, `run_pe_sweep()`, `run_pund_sequence()` (extracts Ps/Pr).
- **Example**: `examples/alscn_pund.py` — AlScN P-V loop with leakage and
  NLS vs Preisach comparison.

### Test snapshot (P1–P4)

```
tests/test_fe_validation.py        16 passed
tests/test_preisach_model.py       12 passed, 1 skipped
tests/test_fe_coupling_and_ionization.py  4 passed
tests/test_analytic_limits.py      12 passed
tests/test_dielectric_breakdown.py  4 passed
tests/test_mms_convergence.py       6 passed
tests/test_mesh_correctness.py     12 passed
regression (FE+mesh+mms+analytic)  66 passed, 1 skipped
```

### Verification pyramid (A·B·C summary)

| Layer | Method | Tests | Bugs caught |
|-------|--------|-------|-------------|
| Analytic limits (A) | L-K Cardano, Preisach/II/breakdown limits, Newton=Gummel | 16 | ① Preisach Escale ② breakdown units |
| Mesh correctness (B-1) | to_3d/index, degenerate grids, bbox, cut-cell, adaptive axis | 12 | ③ refiner reshape ④ zero-contact |
| MMS grid-convergence (B/C) | Poisson sine-box, **RHS-driven direct-vs-analytic rate≈2**, FE div(P) | 6 | — |
| Third-party (M6c) | DevSim 1D/2D terminal current | 21 | — |
| Conservation (M6c) | KCL current balance | 12 | — |

**4 real bugs found and fixed** across A/B, each pinned by a regression test.

## Documentation

- [Roadmap & Future Plans](docs/ROADMAP.md)
- [Evolution Research Program (Loop B/C/D)](plan0618.md)
- [Milestone Plan — M5 / M6 / M6b / M6c](plan0619.md)
- [Research Proposal — device evolution](device_evole.md)
- [Code Audit Report (Loop A logs in §17-§19; M6c log in §20)](audit0618.md)
- [Audit Re-check (M6c follow-up)](audit_recheck.md)
- [API Reference](docs/) (coming soon)

## License

MIT
