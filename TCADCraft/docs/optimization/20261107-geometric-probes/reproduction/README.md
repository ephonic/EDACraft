# Reproduce one bounded device probe

Install the matching development sources and SI float128 native extension
identified in [provenance](../PROVENANCE.json). Keep this directory's drivers,
meshes.npz and both helper modules together. From the TCADCraft project root,
run each case serially in a fresh process and use a fresh output prefix:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONNOUSERSITE=1 TCAD_EXPECT_PRECISION=float128 TCAD_EXPECT_CONSTANTS_PROFILE=si \
  python -B docs/optimization/20261107-geometric-probes/reproduction/geometric_y33_probe.py \
  thermionic space 3 128 probe /tmp/geometric-y33-probe
```

Substitute geometric_y9_probe.py or geometric_y17_probe.py for the two controls.
Apply the per-case wall/CPU, address-space and RSS limits in the frozen policy
separately: these numerical drivers do not impose OS limits themselves.
The `probe` mode runs exactly one BE step, not the full 60 ps trajectory.
JSON/NPZ files contain complete initial and first-step fields; separate atomic
checkpoint files and an accepted-linear journal support interrupted-run review.

The independent audit uses no product solver imports. Its raw frozen checker,
supporting-source identity chain, full results and final audit are retained in
the raw evidence directory identified by provenance. The report's `derived/`
files expose the exact physical oracle, label parameterization and metric
function for inspection; they require the recorded independent-auditor globals
and are not standalone command-line programs.
