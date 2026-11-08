# Replay the full geometric y17 control

Use the exact development sources and SI float128 native extension listed
in [provenance](../PROVENANCE.json). Keep the driver, meshes.npz and both helper
modules together. From the TCADCraft project root, use a fresh output prefix:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONNOUSERSITE=1 TCAD_EXPECT_PRECISION=float128 TCAD_EXPECT_CONSTANTS_PROFILE=si \
  python -B docs/optimization/20261107-geometric-full-y17/reproduction/geometric_y17_full.py \
  thermionic space 3 128 full /tmp/geometric-y17-full
```

Enforce the wall/CPU, peak-RSS and address-space limits from policy separately;
the numerical driver does not impose OS limits itself. Full mode executes all
384 BE steps through 60 ps and exports four complete fields plus journals.

The derived oracle/guard files expose the unchanged formulas for inspection.
They require the recorded auditor globals and are not standalone commands.
The raw evidence path in provenance retains the frozen audit script, input
policy, full results, hash-linked parents and verified archive receipt.
