# TCADCraft

TCADCraft is the TCAD simulation package in EDACraft. It combines a Python API,
Cython bindings, and a C++ solver core for 3D semiconductor device simulation
with quantum correction and calibration-oriented device models.

## Highlights

- Structured Cartesian meshing for the C++ solver
- Optional Gmsh-based unstructured meshing
- Device templates for MOSFET, FinFET, GAA, TFET, FeFET, tunnel diode,
  Dirac-source FET, IGZO TFT, WSe2 Schottky FET, and PN junctions
- Density-gradient quantum correction
- Gummel and Newton coupled solvers
- BTBT, impact ionization, thermal coupling, traps, ferroelectric, and
  reliability models
- Mesh, field, and device post-processing helpers
- Regression tests and release checks

## Layout

- `tcad/` Python package and public API
- `src/` C++ solver core
- `examples/` runnable device setups
- `tests/` regression and validation tests
- `scripts/` release and pre-commit checks

## Requirements

- Python 3.10+
- GCC or Clang on Linux/macOS
- `numpy`, `scipy`, `matplotlib`, `meshio`, `trimesh`, `shapely`
- Optional: `pyvista`, `vtk`, `gmsh`, `PETSc`

Native Windows builds are not supported. Use WSL2 or a Linux/macOS build host.

## Build

```bash
python setup.py build_ext --inplace
```

For hosts without PETSc or LAPACK:

```bash
TCAD_USE_PETSC=0 TCAD_USE_LAPACK=0 python setup.py build_ext --inplace
```

Editable install with optional extras:

```bash
pip install -e ".[dev,viz,gmsh]"
```

## Quick Start

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

print(results["converged"], results["iterations"])
```

## Public API

`tcad` exports `Device`, `Material`, `Region`, `DopingProfile`,
`StructuredGrid`, `generate_mesh`, `Simulator`, `simulate_device`,
`simulate_sweep`, `SolverType`, and `UnstructuredSimulator`.

## Notes

- The package version is `0.2.0`.
- See `examples/` for complete workflows and `tests/` for regression
  coverage.
