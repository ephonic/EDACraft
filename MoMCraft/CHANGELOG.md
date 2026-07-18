# Changelog

All notable changes to MoMCraft will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2026-07-18

### Fixed
- Aligned the routed raw S21 solver with ADS reference cases using physical
  TEM raw-phase referencing, endpoint/modal port selection, and finite-thickness
  copper surface impedance.
- Added geometry-aware conductor-loss scaling from routed metal width and
  substrate metal thickness instead of relying on a fixed empirical loss scale.
- Added guarded full-route retry logic for terminal solves and high-|S21|
  long-line port clustering.
- Fixed the core TL port projection lifetime bug that could destabilize Schur
  reductions.

### Added
- Published the routed-case validation utilities:
  `routed_case_solver.py`, `route_geometry.py`, `routed_strip_mesh.py`,
  `phase_deembed.py`, and `compare_all.py`.
- Added self-contained raw-solver conductor-loss and port-selection regression
  tests.

## [0.1.1] - 2026-07-17

### Fixed
- Stabilized layered-cavity QWE Green-function branch handling for routed
  interconnect extraction.
- Improved RWG assembly, dense-solver diagnostics, and Schur multi-edge port
  reduction for two-port and N-port workflows.
- Added dual multi-edge port extraction support in the Python binding.
- Fixed Touchstone parsing/writing edge cases and package exports.
- Added a layered Green regression test to guard the ADS-alignment path.

## [0.1.0] — 2025-07-04

First public release, contributed to the EDACraft monorepo as `MoMCraft/`.

### Added
- **Method of Moments (MoM) electromagnetic solver** for interconnect
  S-parameter extraction, with a C++17 core and Python bindings.
- **Multilayer-medium dyadic Green's function**: spectral-domain TM/TE
  reflection + S-matrix recursion, QWE (quadrature-with-extraction)
  Sommerfeld integration, two-level Aksun tail extraction, and surface-wave
  pole extraction (Chew search + Hankel space domain).
- **Triangular mesh + RWG (Rao–Wilton–Glisson) basis functions** for
  arbitrary planar and 3D conductor surfaces, including vertical-current
  (Z-component) support for vias and TSVs.
- **High-level Python API**:
  - `mom.Microstrip` — microstrip line MoM solver, frequency sweep, Touchstone output.
  - `mom.Structure` — arbitrary-conductor MoM extraction via RWG mesh +
    dyadic Green + Schur N-port reduction.
  - `mom.FreqSweep` — linear / logarithmic sweep configuration.
  - `mom.write_touchstone` / `mom.read_touchstone` — Touchstone 2.0
    `.sNp` read/write (RI/MA/DB, Hz/kHz/MHz/GHz).
  - `mom.gmsh_mesh` — gmsh-based mesh generation for rectangles, cylinder
    surfaces (TSV), vias with pads, traces, and a built-in 32-bit UCIe
    structure builder.
- **Solver backends**: dense direct LU and preconditioned FFT (pFFT) with
  GMRES for O(N log N) complexity on large meshes.
- **OpenMP parallelization** for matrix assembly and frequency sweeps.
- **Examples**: `freq_sweep_demo.py`, `run_touchstone_demo.py`,
  `run_structure_demo.py` (RWG), and `run_ucie_demo.py` (32-bit UCIe).

### Build system
- scikit-build-core + CMake (Ninja recommended) + pybind11 2.13.x.
- Eigen 3.4.0 fetched automatically via CMake `FetchContent` (network
  required on first configure).
- Portable `scripts/build.bat` / `scripts/rebuild.bat` for Windows with
  automatic Python/MSVC detection; Linux/macOS build via `pip install -e .`.
