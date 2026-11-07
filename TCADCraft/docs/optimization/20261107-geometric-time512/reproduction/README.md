# Replay the full n512 y33 pulse

Use the numerical source and SI float128 native extension in
[provenance](../PROVENANCE.json). Keep this driver, meshes.npz and both helper
modules together. From the TCADCraft root, choose a fresh output prefix:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONNOUSERSITE=1 TCAD_EXPECT_PRECISION=float128 TCAD_EXPECT_CONSTANTS_PROFILE=si \
  python -B docs/optimization/20261107-geometric-time512/reproduction/geometric_y33_n512.py \
  thermionic space 3 512 full /tmp/geometric-y33-n512
```

Enforce the frozen wall/CPU/RSS/address-space budgets separately. The driver
itself imposes no OS limits. The sealed raw directory retains complete outputs,
audit/diagnostic scripts, identities and receipt. Derived audit functions need
the recorded globals. Use the unchanged trace comparator with the exact sealed
n128/n256 parents and new n512 output; inspect adjacent clock gates and the
normalized roundoff floor without adding an acceptance threshold.
