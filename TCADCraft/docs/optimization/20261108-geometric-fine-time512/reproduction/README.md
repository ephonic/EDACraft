# Reproduce the refined-grid n512 pulse

Use the source/native identities in [provenance](../PROVENANCE.json), keeping
the driver, meshes.npz and helper modules together. From the TCADCraft root:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONNOUSERSITE=1 TCAD_EXPECT_PRECISION=float128 TCAD_EXPECT_CONSTANTS_PROFILE=si \
  python -B docs/optimization/20261108-geometric-fine-time512/reproduction/geometric_z129_n512.py \
  thermionic space 3 512 full /tmp/geometric-z129-n512
```

Enforce [policy](../policy.json) wall/CPU/RSS/address-space limits separately.
The driver imposes no OS limits. A fresh run must pass the same independent
audit. Raw evidence retains complete outputs and audit/diagnostic scripts;
derived functions need the recorded globals. Use the sealed n128/n256 parents
and unchanged comparator for interval-matched three-time diagnostics.
