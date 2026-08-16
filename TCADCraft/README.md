# TCADCraft

TCADCraft is the TCAD simulation package in EDACraft. It combines a Python API,
Cython bindings, and a C++ solver core for 3D semiconductor device simulation
with quantum correction and calibration-oriented device models.

## What It Covers

- Structured Cartesian meshing for the main solver path
- Optional Gmsh-based unstructured meshing
- Planar MOSFET, FinFET, GAA, BSPDN GAA, TFET, tunnel diode, Dirac-source FET
- IGZO TFT and WSe2 Schottky FET templates
- Density-gradient quantum correction
- BTBT, impact ionization, thermal coupling, traps, ferroelectric, leakage
- Mesh, field, and sweep post-processing

## Install And Build

```bash
python setup.py build_ext --inplace
```

For systems without PETSc or LAPACK:

```bash
TCAD_USE_PETSC=0 TCAD_USE_LAPACK=0 python setup.py build_ext --inplace
```

Editable install with optional extras:

```bash
pip install -e ".[dev,viz,gmsh]"
```

Native Windows builds are not the primary target. Use WSL2 or Linux/macOS.

## Basic Workflow

1. Pick a device template or build a custom `Device`.
2. Generate a mesh with `generate_mesh()` or `structured_mesh_from_device()`.
3. Create `Simulator(mesh)`.
4. Load material fields with `set_material_from_mesh()`.
5. Set contacts and physics options.
6. Run `run()`, `run_transient()`, `simulate_device()`, or `simulate_sweep()`.
7. Inspect `results`, export fields, and post-process metrics.

Minimal example:

```python
from tcad import Device, simulate_device

dev = Device.mosfet(Lg=50e-9, tox=1.5e-9, tsi=10e-9, W=100e-9, Vg=0.7, Vd=0.5)
sim, results = simulate_device(
    dev,
    resolution=(5e-9, 5e-9, 5e-9),
    quantum=False,
    ramp_steps=3,
    max_iter=80,
    tol=1e-8,
)
```

## Device Recipes

### Bulk MOSFET

Use `Device.mosfet(...)` for a planar body MOSFET. This is the easiest entry
point for transfer curves and basic electrostatics.

Typical workflow:

```python
import numpy as np
from tcad import Device, simulate_sweep
from tcad.postprocess.metrics import extract_transfer_characteristics_current
from tcad.viz.plotter import plot_transfer

dev = Device.mosfet(
    Lg=50e-9, tox=1.5e-9, tsi=20e-9, W=100e-9, Lsd=50e-9,
    Vd=0.5, Vs=0.0,
)
sim, sweep = simulate_sweep(
    dev,
    {"gate": np.linspace(0.0, 0.8, 17)},
    resolution=(2e-9, 5e-9, 1e-9),
    quantum=True,
    ramp_steps=3,
    max_iter=80,
    tol=1e-8,
)
metrics = extract_transfer_characteristics_current(sim, sweep)
plot_transfer(metrics["Vg"], metrics["Id"], Vth=metrics["Vth"])
```

When you want a single bias point instead of a sweep, call `simulate_device()`
with the same template and a fixed `Vg` / `Vd`.

### FinFET

Use `Device.finfet(...)` for a double-gate fin device. The mesh should be
finer across the fin thickness than along the channel.

```python
from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device
from tcad.viz.plotter import plot_mesh_slice

device = Device.finfet(
    Lg=30e-9, tox=1.5e-9, tsi=10e-9, Hfin=30e-9,
    Lsd=30e-9, tgate=10e-9, Vg=0.7, Vd=0.1,
)
mesh = structured_mesh_from_device(device, resolution=(5e-9, 2.5e-9, 5e-9))
sim = Simulator(mesh, temperature=300.0)
sim.set_material_from_mesh()
for name, (_, voltage) in device.contacts.items():
    sim.set_contact(name, voltage)
results = sim.run(max_iter=120, tol=1e-8)
for name, data in sim.to_mesh_fields().items():
    sim.mesh.add_field(name, sim.mesh.from_3d(data))
plot_mesh_slice(sim.mesh, field="phi", axis="z", coord=15e-9)
```

For thin fins, keep `quantum=True` and consider `set_newton_options(...)` when
the drain bias is high.

### GAA And Nanosheet

Use `Device.gaa(...)` for a silicon nanosheet and `Device.gaa_highk(...)` when
you want a high-k gate stack. For silicon nanosheets, enable the multivalley
density-gradient closure.

```python
from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device

device = Device.gaa(
    Lg=20e-9, tox=1.5e-9, t_sheet=5e-9, W_sheet=30e-9,
    Lsd=30e-9, Vg=0.7, Vd=0.05,
)
mesh = structured_mesh_from_device(device, resolution=(5e-9, 2.5e-9, 2.5e-9))
sim = Simulator(mesh, temperature=300.0)
sim.set_material_from_mesh()
sim.set_quantum(True)
sim.set_density_gradient_silicon_multivalley(True)
sim.enable_cut_cell(True)
for name, (_, voltage) in device.contacts.items():
    sim.set_contact(name, voltage)
results = sim.run(max_iter=120, tol=1e-8)
```

This is the right starting point for nanosheet transfer curves, DG comparison,
and quantum confinement studies.

### GaN

TCADCraft currently provides GaN as a material library entry via
`tcad.material.library.gallium_nitride()`. There is no one-line `Device.gan()`
helper yet, so GaN devices are built as custom `Device` objects.

The most direct workflow is a vertical Schottky diode or Schottky-contact
stack:

```python
from tcad import Device, Simulator
from tcad.geometry import Region
from tcad.geometry.shapes import Box
from tcad.material.library import gallium_nitride
from tcad.mesh.generator import structured_mesh_from_device

gan = gallium_nitride()
device = Device("gan_schottky")
device.add_region(Region("gan", Box(0, 100e-9, 0, 10e-9, 0, 10e-9), gan))
device.add_contact("anode", Box(0, 100e-9, 0, 10e-9, 9e-9, 10e-9), voltage=0.0,
                   workfunction=4.8)
device.add_contact("cathode", Box(0, 100e-9, 0, 10e-9, -1e-9, 0.0), voltage=0.0)

mesh = structured_mesh_from_device(device, nx=9, ny=3, nz=5)
sim = Simulator(mesh, temperature=300.0)
sim.set_material_from_mesh()
sim.set_contact("anode", 0.3, workfunction=4.8)
sim.set_contact("cathode", 0.0)
sim.set_schottky_tunneling(
    "anode",
    effective_mass_ratio=0.20,
    area_m2=1.0e-13,
    tunneling_barrier_lowering_eV=0.0928,
    series_resistance_ohm=1360.0,
)
results = sim.run(max_iter=80, tol=1e-8)
```

For GaN pn structures, use `gallium_nitride()` in custom `Region`s and apply
the same `Simulator` / `simulate_device()` flow.

### TFET And Tunnel Diode

Use `Device.tfet(...)` or `Device.tunnel_diode(...)` and keep voltage steps
small.

Recommended controls:

- `set_btbt(enabled=True, use_nonlocal=True)` for source-channel tunneling
- `set_btbt_weight(...)` if you want to gate the BTBT source region
- `simulate_sweep(...)` with small voltage increments

For tunnel diode NDR analysis, use `extract_ndr_metrics(...)`.

### FeFET / NC-FET

Use `Device.gaa_fefet(...)` or a custom ferroelectric stack.

Recommended controls:

- `set_ferroelectric(enabled=True, model="landau_khalatnikov" | "preisach" | "nls")`
- `set_ferroelectric_builtin_field(...)`
- `set_ferroelectric_depol(...)`
- `set_leakage(...)`
- `set_interface_traps(...)` and `set_oxide_traps(...)` if needed

For P-V / P-E / PUND studies, use `tcad.postprocess.fe_loops`.

### Schottky And WSe2

Use `Device.wse2_schottky_fet(...)` or `set_contact(..., workfunction=...)`
for Schottky boundary conditions.

Recommended controls:

- `set_schottky_tunneling(...)`
- `set_wse2_schottky_contact(...)`
- `set_contact(..., workfunction=...)` before enabling tunneling

### IGZO And Disordered Transport

Use `Device.igzo_tft(...)` and the mesh metadata fields for tail states.

Recommended controls:

- `set_disordered_transport(True)`
- `set_mobility_model("constant" | "arora" | ...)`
- `set_statistics("boltzmann" | "fermi_dirac")`

### Adaptive And Transient Workflows

- `run_adaptive(...)` for solve-refine-resolve loops
- `set_transient(dt, t_final, fe_gamma=0.0)` plus `run_transient(...)`
- `set_thermal_coupling(True, ...)` for self-heating studies

## How To View Results

`run()` returns a dictionary. Common keys include:

- `phi`, `n`, `p`
- `Ex`, `Ey`, `Ez`
- `Qn`, `Qp`
- `temperature` when thermal coupling is enabled
- `G_btbt`, `G_ii`, `Jleak_x`, `Jleak_y`, `Jleak_z` when those models are active
- `converged`, `iterations`, `valid`
- `continuation_steps`, `continuation_steps_completed`, `continuation_retries`

Mesh-backed views:

```python
fields = sim.to_mesh_fields()
sim.save("result.vtk")
```

Plotting helpers:

- `tcad.viz.plotter.plot_mesh_slice(mesh, field="phi", axis="y")`
- `tcad.viz.plotter.plot_1d_cutline(...)`
- `tcad.viz.plotter.plot_3d_field(...)`
- `tcad.viz.plotter.plot_transfer(...)`
- `tcad.viz.plotter.plot_pv_loop(...)`
- `tcad.viz.plotter.plot_pe_loop(...)`
- `tcad.viz.plotter.plot_pund(...)`

`plot_3d_field()` uses PyVista if installed, otherwise it falls back to a 2D
slice plot.

## Main Post-Processing APIs

Use current-based extractors for quantitative work:

- `tcad.postprocess.metrics.extract_transfer_characteristics_current(...)`
- `tcad.postprocess.tfet.extract_tfet_metrics(...)`
- `tcad.postprocess.ndr.extract_ndr_metrics(...)`
- `tcad.postprocess.hysteresis.extract_hysteresis(...)`
- `tcad.postprocess.hysteresis.extract_ss(...)`

The legacy `extract_transfer_characteristics(...)` function is a density proxy
and should only be used when you explicitly want that degraded metric.

## Main Public API

`tcad` exports:

- `Device`, `Material`, `Region`, `DopingProfile`
- `StructuredGrid`, `generate_mesh`
- `Simulator`, `simulate_device`, `simulate_sweep`
- `SolverType`, `UnstructuredSimulator`

Key `Simulator` methods:

- `set_material_from_mesh()`
- `set_contact(name, voltage, workfunction=None)`
- `set_quantum()`
- `set_btbt()`
- `set_impact_ionization()`
- `set_thermal_coupling()`
- `set_ferroelectric()`
- `set_leakage()`
- `set_interface_traps()`
- `set_oxide_traps()`
- `set_statistics()`
- `set_mobility_model()`
- `run()`
- `run_transient()`
- `run_adaptive()`
- `to_mesh_fields()`
- `save()`

## Layout

- `tcad/` Python package and public API
- `src/` C++ solver core
- `examples/` runnable device setups
- `tests/` regression and validation tests
- `scripts/` release and pre-commit checks

## Notes

- The package version is `0.2.0`.
- `simulate_device()` is the easiest entry point for single-device runs.
- `simulate_sweep()` is the normal entry point for transfer curves.
- Useful examples: `examples/mosfet_simulation.py`,
  `examples/finfet_simulation.py`, `examples/finfet_gaa_simulation.py`,
  `examples/pn_junction.py`, `examples/graphene_source_tfet.py`.
- See `examples/` for device-specific scripts and `tests/` for regression
  coverage.
