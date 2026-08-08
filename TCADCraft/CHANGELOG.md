# Changelog

All notable changes to TCADCraft are documented in this file. Versions follow
Semantic Versioning, and dates use ISO 8601.

## [0.2.0] - 2026-08-08

### Added

- Calibration for HfO2 ferroelectric hysteresis,
  silicon trap stress/recovery, GaN Schottky nonlocal tunneling, 8 nm
  density-gradient confinement, and electrothermal avalanche breakdown.
- Calibratable Schottky thermionic/nonlocal-tunneling contacts, reliability and
  trap models, GaN material defaults, and wrap-gate device construction.
- Electrothermal breakdown replay with avalanche-integral, hotspot,
  temperature-stop, and terminal-current conservation gates.
- Reliability, Schottky-contact, wrap-gate, analytic-limit, MMS-convergence,
  and coupled-solver regression coverage.

### Changed

- Newton is now the authoritative result on Newton-primary runs; a skipped or
  failed Gummel warm-up can no longer report false convergence.
- Coupled Newton includes Auger recombination and analytic derivatives, uses a
  mixed absolute/relative KCL guard, and retains carrier consistency after a
  converged solve.
- Density-gradient handling, nonuniform-grid edge metrics, contact-current
  extraction, adaptive continuation, and thermal stop-point refinement were
  hardened for nanoscale and high-field devices.
- Release builds no longer use host-specific `-march=native` instructions
  unless explicitly requested with `TCAD_NATIVE_OPT=1`.
- Portable builds default to the internal direct solver, avoiding BLAS/LAPACK
  symbol collisions when PyPI SciPy wheels are installed. System LAPACK is now
  an explicit source-build option (`TCAD_USE_LAPACK=1`).
- Native Windows now fails early with an actionable WSL2/Linux message instead
  of being misconfigured with Unix compiler and linker flags.

### Fixed

- Removed the post-Newton Poisson-only solve that could invalidate converged
  carrier/electrostatic consistency.
- Restricted carrier safety clamping to non-converged failure states.
- Corrected version metadata drift between the package and runtime module.
- Included C++ headers and sources in source distributions and corrected
  project URLs.
- Fixed a clean-environment segmentation fault caused by mixing system LAPACK
  with the private BLAS/LAPACK runtime shipped in SciPy wheels.

### Known limitations

- The 3/5/8/10 nm quantum-thickness family is not yet a full release gate:
  10 nm passes, while 3 nm and 8 nm are partial and 5 nm fails profile/sheet
  charge criteria. The independently calibrated 8 nm baseline passes.
- Electrothermal replay uses a Sentaurus-calibrated ionization scale of 0.07 as
  a surrogate for the native high-field velocity-saturation model still to be
  implemented.
- IGZO and WSe2 device models are implemented but require experiment- or
  first-principles-constrained material files before quantitative calibration.

[0.2.0]: https://github.com/ephonic/EDACraft/tree/main/TCADCraft
