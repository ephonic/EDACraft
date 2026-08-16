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

## Device Simulation Methods

### Planar MOSFET

Use `Device.mosfet(...)` with `simulate_device()` for a single bias point or
`simulate_sweep()` for `Id-Vg` / `Id-Vd` curves.

Recommended controls:

- `set_quantum(True)` for thin bodies
- `set_newton_options(...)` for strong inversion
- `ramp_steps > 1` for high bias sweeps

### FinFET, GAA, BSPDN GAA

Use `Device.finfet(...)`, `Device.gaa(...)`, `Device.gaa_highk(...)`, or
`Device.bspdn_gaa(...)`.

Recommended controls:

- `set_quantum(True)`
- `set_density_gradient_silicon_multivalley(...)` for Si nanosheets
- `enable_cut_cell(True)` when interfaces cut through a structured grid
- `set_solver_type(...)` if you want to force a backend

### TFET And Tunnel Diode

Use `Device.tfet(...)` or `Device.tunnel_diode(...)`.

Recommended controls:

- `set_btbt(enabled=True, use_nonlocal=True)` for source-channel tunneling
- `set_btbt_weight(...)` if you want to gate the BTBT source region
- `simulate_sweep(...)` with small voltage steps

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

## Common Recipes

### Transfer Sweep

```python
import numpy as np
from tcad import Device, simulate_sweep
from tcad.postprocess.metrics import extract_transfer_characteristics_current

dev = Device.mosfet(Vd=0.5)
sim, sweep = simulate_sweep(
    dev,
    {"gate": np.linspace(0.0, 0.8, 17)},
    resolution=(5e-9, 5e-9, 5e-9),
    ramp_steps=3,
    quantum=False,
)

metrics = extract_transfer_characteristics_current(sim, sweep)
print(metrics["Vth"], metrics["SS"], metrics["Ion_Ioff"])
```

### Mesh Slices And Export

```python
from tcad.viz.plotter import plot_mesh_slice, plot_transfer

fields = sim.to_mesh_fields()
plot_mesh_slice(sim.mesh, field="phi", axis="y", coord=5e-9)
plot_transfer(metrics["Vg"], metrics["Id"], Vth=metrics["Vth"])
sim.save("mosfet.vtk")
```

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
- See `examples/` for device-specific scripts and `tests/` for regression
  coverage.
