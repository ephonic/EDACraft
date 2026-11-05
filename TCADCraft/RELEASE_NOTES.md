# TCADCraft 0.3.0rc1

Release candidate prepared on 2026-11-05. This scoped research release does
not certify every physics combination, 2D device or commercial alignment target.

## Changes

- Graphene Dirac and MoS₂ parabolic-band sheet statistics, Fermi–Dirac surface
  densities, charge derivatives and quantum capacitance.
- Sheet phi/Fn/Fp drift–diffusion, optional diffusion-enhanced modified SG,
  ideal/resistive/thermionic/Dirac edge contacts and single-level trap dynamics.
- Cartesian dielectric Poisson coupling, finite side electrodes, backward
  Euler transients and terminal conduction/displacement current accounting.
- Sparse coupled Newton and optional reused GMRES, with steady/BE cache keys,
  true max-norm acceptance, residual correction and transactional publication.
- Accumulated native nonlinear solver, finite-input, contact, recovery and
  physics-accounting fixes from the frozen development source.
- Updated installation, source provenance and explicit model limits.

## Validation and known gaps

Two fine-grid MoS₂ 60 ps trajectories completed independent full-field/trace
checks. Local-z initialization/one-step probes also passed. See
[validation details](docs/releases/0.3.0rc1/VALIDATION.md) for counts, provenance
and release-specific build/install verification.

Full spatial convergence is unqualified; fine-grid temporal and joint
spacetime bounds are not established. Sheet models are isothermal,
homogeneous-band and constant-mobility, with representative parameters.
Complete 2D logic circuits, full memory write/erase/read/retention/disturb/
endurance, dedicated Schrödinger–Poisson and NEGF transport remain open.
Density-gradient and quantum capacitance do not replace those solvers.

Historical targeted regressions are inherited evidence, not fresh full-suite
tests. This release claims no new commercial solver or experimental acceptance.
The old 0.2.0 fixed gap-list wording did not certify whole-product equivalence.

## Build and artifact scope

- Package/runtime version: `0.3.0rc1`; Python >=3.10.
- C++17 GCC with libquadmath; default SI constants and `__float128` core
  (113 mantissa bits). Python/SciPy sheet solvers use float64.
- Native Windows is unsupported; use Linux or WSL2.
- Linux wheels are specific to the Python ABI/runtime in their compatibility
  report; no universal or manylinux compatibility is implied.
- Large raw validation archives and external calibration dashboards are not
  bundled; compact input identity and numerical summaries are included.

```bash
TCAD_USE_PETSC=0 TCAD_USE_LAPACK=0 python -m pip install '.[dev]'
```
