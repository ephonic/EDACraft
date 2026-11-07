# Replay the full geometric y33 pulse

Use the development sources and SI float128 native extension identified in
[provenance](../PROVENANCE.json). Keep the driver, meshes.npz and both helper
modules together. From the TCADCraft project root, use a fresh output prefix:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONNOUSERSITE=1 TCAD_EXPECT_PRECISION=float128 TCAD_EXPECT_CONSTANTS_PROFILE=si \
  python -B docs/optimization/20261107-geometric-full-y33/reproduction/geometric_y33_full.py \
  thermionic space 3 128 full /tmp/geometric-y33-full
```

Apply the wall/CPU, RSS and address-space limits from policy separately;
the numerical driver does not enforce OS limits. Full mode exports four
complete fields and every-step journals across all 384 BE steps.

For the three-grid verdict, combine this accepted output with the exact
sealed full ND y9/y17 inputs referenced by policy and use the unchanged
metric function in derived/. The derived oracle and metric files require
the recorded auditor globals; they are not standalone CLI programs. The raw
evidence path retains full results, the frozen audit/diagnostic scripts,
parent identities and verified archive receipt.
