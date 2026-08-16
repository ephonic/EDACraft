# TCADCraft 0.2.0 Release Notes

Release date: 2026-08-16

TCADCraft 0.2.0 is a source-code release focused on numerical robustness,
device-physics coverage, mixed-material workflows, and reproducible calibration
artifacts. No tarball or wheel artifact is included.

## Highlights

- Stabilized coupled Newton/Gummel solve paths with stricter finite-state,
  residual, Jacobian, line-search, and write-back checks.
- Improved density-gradient quantum correction workflows across thin-body
  MOS and non-planar device examples.
- Added and hardened Schottky/contact, tunneling, electrothermal, trap,
  ferroelectric, TFET, GaN, IGZO, WSe2, FinFET, and GAA calibration workflows.
- Added sparse WSe2 residual replay export artifacts for compact deck-local
  replay with bounded anchor count.
- Improved mesh/control-volume handling around material interfaces,
  nonuniform grids, cut cells, and non-planar geometries.
- Added release metadata checks for package/runtime version consistency and
  calibration dashboard integrity.

## Validation status

The release gate is expected to pass with:

- TCADCraft package/runtime version: `0.2.0`
- Calibration dashboard check: passed
- Device-family support matrix: passed
- Gap-closure report: closed
- Release metadata check: passed

Fast release check:

```bash
python scripts/release_check.py \
  --calibration-root ../.. \
  --mixed-material-dashboard ../../bench/results/calibration/tcadcraft_mixed_material_calibration_dashboard.json
```

## Notable behavior changes

- Newton-primary mode no longer inherits skipped or stale Gummel warm-start
  states.
- Gummel acceptance now requires successful continuity polishing and finite
  carrier state.
- Newton solve paths reject non-finite potential, carrier, residual, Jacobian,
  step, and write-back values earlier.
- Default source builds avoid mandatory system LAPACK/BLAS linkage; system
  LAPACK can still be enabled explicitly where appropriate.
- Quantum-correction paths use stricter residual and interface checks for
  thin-body and non-planar device families.
- WSe2 replay artifacts now include a fixed-budget sparse residual replay
  export in addition to dense diagnostic metrics.

## Included source areas

- `tcad/` — Python API, material library, geometry builders, physics models,
  post-processing, and simulator orchestration.
- `src/` — C++ numerical kernels and bindings.
- `tests/` — regression and validation tests.
- `scripts/` — release and metadata checks.
- `examples/` — reference device setup examples.

## Known limitations

- Quantitative calibration remains valid only within the released device
  families, parameter windows, and replay artifacts included with this version.
- Some advanced material/device workflows require external material parameter
  files before they should be treated as predictive outside the included
  calibration windows.
- Sparse WSe2 replay is deck-local and is not a replacement for a fully
  transferable no-residual compact model.
- Native Windows/MSVC source builds are not the primary target; Windows users
  should prefer WSL2.

## Build notes

```bash
TCAD_USE_PETSC=0 TCAD_USE_LAPACK=0 python setup.py build_ext --inplace
python -m pytest -q
```

Linux and macOS source builds with GCC/Clang are the primary supported build
targets. LAPACK acceleration can be enabled explicitly with
`TCAD_USE_LAPACK=1` after platform validation.
