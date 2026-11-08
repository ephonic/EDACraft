# Replay the full half-dt y33 pulse

Use the numerical sources and SI float128 native extension identified in
[provenance](../PROVENANCE.json). Keep this driver, meshes.npz and both helper
modules together. From the TCADCraft root, choose a fresh output prefix:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONNOUSERSITE=1 TCAD_EXPECT_PRECISION=float128 TCAD_EXPECT_CONSTANTS_PROFILE=si \
  python -B docs/optimization/20261107-geometric-time256/reproduction/geometric_y33_n256.py \
  thermionic space 3 256 full /tmp/geometric-y33-n256
```

Enforce the wall/CPU/RSS/address-space budgets from policy separately;
the driver itself does not impose OS limits. The sealed raw directory retains
the complete outputs, audit/diagnostic scripts, source identities and receipt.
Derived audit functions require the recorded globals and are not standalone
CLI programs. Use the unchanged trace comparator on the exact sealed n128
parent and new n256 output; two time resolutions provide no observed order.
