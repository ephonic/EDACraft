# MoMCraft — Interconnect S-parameter Extraction (Method of Moments)

A Method of Moments (MoM) electromagnetic solver for extracting S-parameters
of 3D interconnect structures — microstrip lines, multilayer substrates,
through-silicon vias (TSVs), microbumps, and **UCIe (Universal Chiplet
Interconnect Express)** packages — across the 0–60 GHz band.

MoMCraft combines a layered-medium dyadic Green's function (spectral-domain
recursion + QWE Sommerfeld integration + surface-wave pole extraction) with
RWG basis functions on triangular meshes and Schur N-port reduction, all
behind a small high-level Python API. The numerical core is C++17 with
Eigen and OpenMP; Python bindings are generated with pybind11.

```
┌──────────────────────────────────────────────────────────────┐
│  Python API — Microstrip / Structure / FreqSweep / Touchstone │
├──────────────────────────────────────────────────────────────┤
│  pybind11 bindings (_mom) — zero-copy NumPy                   │
├──────────────────────────────────────────────────────────────┤
│  C++ core — Green (spectral/QWE/poles), RWG assembly,         │
│             dense + pFFT solvers, Schur N-port, freq. sweep    │
└──────────────────────────────────────────────────────────────┘
```

## Features

- **Layered-medium dyadic Green's function**: spectral TM/TE reflection with
  S-matrix recursion (accurate for any permittivity), QWE Sommerfeld
  integration (J1 zeros + Shanks extrapolation), two-level Aksun tail
  extraction, and surface-wave pole extraction (Chew search + Hankel domain).
- **RWG basis functions** on triangular meshes for arbitrary planar and 3D
  conductor surfaces, including **vertical-current support** for vias/TSVs.
- **Two solver backends**: dense direct LU for small problems and
  preconditioned FFT (pFFT) + GMRES for O(N log N) on large meshes.
- **Schur N-port reduction** and Z→S conversion for multi-port extraction.
- **High-level Python API**: `Microstrip`, `Structure`, `FreqSweep`,
  Touchstone 2.0 `.sNp` read/write.
- **gmsh-based meshing**: rectangles, cylinder surfaces (TSV), vias with
  pads, traces, and a built-in **32-bit UCIe structure** builder.
- **OpenMP parallelization** for matrix assembly and frequency sweeps.
- **Wideband S-parameter extraction** (validated 1–64 GHz).

## Supported structures

- Single / coupled microstrip transmission lines
- Multilayer substrates (e.g. FR4, with PEC ground plane)
- Through-silicon vias (TSVs) and microbumps / solder balls
- 32-bit UCIe interconnects and other 2.5D/3D advanced packages

## Installation

### Prerequisites

- **Python 3.9+** with NumPy 1.24+
- **CMake 3.16+** and a **C++17 compiler** (MSVC 2019+/2022, GCC, or Clang)
- **Ninja** (recommended generator) — bundled with Visual Studio on Windows
- **Network access on first build** (CMake fetches Eigen 3.4.0)
- Optional: **gmsh** (`pip install gmsh`) for UCIe / 3D meshing, **matplotlib**
  for plotting, **OpenMP** for parallelism

### Build (editable install, recommended)

```bash
pip install -e .
```

On Windows you can instead use the helper scripts, which auto-detect Python
and MSVC:

```bat
scripts\build.bat        :: configure + build + smoke test
scripts\rebuild.bat      :: clean rebuild + pytest
```

### Verify the build

```bash
python -c "import mom; print(mom.__version__)"
pytest tests/test_smoke.py -q
```

## Quick start

### 1. Microstrip line → Touchstone

```python
import numpy as np
import mom

ms = mom.Microstrip(
    length=20e-3,   # 20 mm
    width=3e-3,     # 3 mm
    height=1.6e-3,  # dielectric thickness
    eps_eff=4.3,    # effective permittivity
    nx=40,          # segments along the line
    z0_ref=50.0,
)

freqs = np.linspace(0.5e9, 10e9, 20)
S = ms.solve_sweep(freqs)          # -> (nfreq, 2, 2) complex128
ms.to_touchstone("out.s2p", freqs, fmt="RI")

# Read it back
fr, S, z0 = mom.read_touchstone("out.s2p")
```

### 2. Arbitrary conductor (RWG mesh) — `Structure`

```python
import numpy as np
import mom

s = mom.Structure(
    conductor=mom.RectangleConductor(0, 0.02, -0.0015, 0.0015, 0.0016),
    medium=mom.Stackup(eps_r=4.3, h=1.6e-3),
    nx=8, ny=2,
    z0_ref=50.0,
)
s.add_port("in", 0)
s.add_port("out", -1)          # -1 = last RWG basis

S = s.solve(1e9)               # -> (2, 2) S-parameters at 1 GHz
s.to_touchstone("rwg.s2p", np.linspace(1e9, 10e9, 10))
```

### 3. 32-bit UCIe mesh (requires `pip install gmsh`)

```python
import mom.gmsh_mesh
mesh, structure = mom.gmsh_mesh.build_ucie_32bit_mesh(n_bits=32)
print(f"{structure.n_bits}-bit UCIe, mesh has {mesh.n_triangles()} triangles")
```

Run the bundled examples:

```bash
python examples/freq_sweep_demo.py        # sweep config + zero-copy smoke
python examples/run_touchstone_demo.py    # microstrip -> .s2p (round-trip)
python examples/run_structure_demo.py     # RWG Structure API
python examples/run_ucie_demo.py          # 32-bit UCIe mesh + sweep
```

## Python API reference

Top-level exports from `import mom`:

| Symbol | Description |
|--------|-------------|
| `Microstrip` | Microstrip line MoM solver: `solve`, `solve_sweep`, `to_touchstone` |
| `Structure` | Arbitrary-conductor solver (RWG mesh + dyadic Green + Schur N-port) |
| `RectangleConductor`, `Stackup` | Geometry / dielectric descriptors for `Structure` |
| `FreqSweep` | Linear / logarithmic frequency-sweep configuration |
| `solve_microstrip`, `solve_microstrip_sweep`, `MicrostripConfig` | Low-level microstrip solve |
| `write_touchstone`, `read_touchstone` | Touchstone 2.0 `.sNp` I/O (RI/MA/DB) |
| `square_in_place`, `SweepScale` | Zero-copy NumPy plumbing / sweep scale enum |
| `__version__` | Package version |

Mesh generation lives in `mom.gmsh_mesh` (import it explicitly):
`GmshMesher`, `UCieStructure`, `build_ucie_32bit_mesh`,
`create_gmsh_mesher`.

See the [使用说明 (中文详细教程)](使用说明.md) for a full walkthrough.

## Project layout

```
core/        C++17 solver core (Green's function, RWG assembly, solvers, sweep)
bindings/    pybind11 Python bindings (_mom extension)
py/mom/      Python package (high-level API + gmsh meshing + Touchstone I/O)
examples/    Runnable end-user examples
tests/       pytest smoke tests
docs/        Design notes (UCIe, vertical current, multi-port plan)
scripts/     Portable Windows build helpers
```

## Documentation

- [使用说明 (中文教程)](使用说明.md)
- [UCIe implementation notes](docs/UCIE_IMPLEMENTATION.md)
- [Vertical current support](docs/VERTICAL_CURRENT_SUPPORT.md)
- [Multi-port design plan](docs/multi-port.md)
- [Changelog](CHANGELOG.md)

## References

1. Michalski, K. A., & Zheng, D. (1990). *Electromagnetic scattering and
   radiation by surfaces of arbitrary shape.* IEEE TAP, 38(3), 335–344.
2. Rao, S. M., Wilton, D. R., & Glisson, A. W. (1982). *Electromagnetic
   scattering by surfaces of arbitrary shape.* IEEE TAP, 30(3), 409–418.
3. Key, K. (2011). *geo2011-0237: QWE Sommerfeld integration.*
4. Aksun, M. I. (1996). *A robust approach for the derivation of
   closed-form Green's functions.* IEEE TMTT, 44(5), 651–658.

## License

MIT License — see [LICENSE](LICENSE).
