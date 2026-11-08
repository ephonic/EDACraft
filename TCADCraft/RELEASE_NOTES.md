# TCADCraft 0.3.0rc2

Release candidate prepared on 2026-11-08. This release packages the numerical
solver updates and audited studies after 0.3.0rc1. It is a scoped research
release with explicit model and acceptance limits.

## Changes

- Optional `MMD_AT_PLUS_A` and geometry-only `GEOMETRIC_ND` orderings for
  coupled sheet reused GMRES. Default ordering and physical/residual gates remain.
- Explicit cache-release APIs preserve the accepted sheet state, time and drive.
- Interval-aware BE trace comparisons, signed terminal integrals, three-time
  observed orders and reduced-memory record loading.
- Complete independent x/y/z refinement controls, including the nine-pulse
  z113/121/129 by n128/256/512 matrix at x83/y9. All original 54 z endpoint
  gates pass at each dt. Coarse-x 52/54 results and resource failures remain.
- Source archives include the compact report reproduction scripts and fixtures.

## Validation and open gaps

The newest two complete 60 ps pulses add 3072 BE steps, eight complete fields
and 2,089,230 independently reconstructed physical/ledger checks. Three z
meshes have bulk-potential observed time orders about 1.01 and decreasing
increments in all ninety trace metrics. Observed orders are descriptive;
combined x/y/z error bounds and an asymptotic regime are not established.

See [scope and provenance](docs/releases/0.3.0rc2/VALIDATION.md) and
[fresh build/install results](docs/releases/0.3.0rc2/RELEASE_VERIFICATION.json).
Development regression and numerical-study counts are inherited evidence,
separate from this release's freshly executed installed-package tests.

The sheet path remains isothermal, homogeneous-band and constant-mobility,
using representative material/contact parameters and aligned Cartesian geometry.
Full 2D logic/memory qualification, real material calibration, dedicated
Schrödinger–Poisson/NEGF and full Sentaurus equivalence remain open. The four
previously excluded three-temperature/energy research qualifications remain
separate; this release supplies no new commercial or experimental acceptance.

## Installation and compatibility

- Package/runtime version `0.3.0rc2`; Python >=3.10 for source builds.
- Bundled wheel: Linux x86_64 / CPython 3.13, native GCC float128 (113 mantissa
  bits), SI constants. Python/SciPy sheet arithmetic remains float64.
- C++17 GCC and libquadmath are required for source builds. Windows uses WSL2
  or Linux; other platforms/Python ABIs require their own builds and checks.
- Host-built wheel, not manylinux-certified; inspect the compatibility report.
- [Artifacts, checksums and install instructions](binaries/README.md).
- Publication updates the GitHub source/tag and artifacts; it does not replace
  `/apps/EDAs/own/tcad/current` on the numerical host.
