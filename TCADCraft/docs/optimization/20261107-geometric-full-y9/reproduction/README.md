# Replay the full geometric y9 control

Use the exact development sources and SI float128 native extension identified
in [provenance](../PROVENANCE.json). Keep the driver, meshes.npz and both helper
modules together. From the TCADCraft project root, use a fresh output prefix:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONNOUSERSITE=1 TCAD_EXPECT_PRECISION=float128 TCAD_EXPECT_CONSTANTS_PROFILE=si \
  python -B docs/optimization/20261107-geometric-full-y9/reproduction/geometric_y9_full.py \
  thermionic space 3 128 full /tmp/geometric-y9-full
```

Apply the wall/CPU, peak-RSS and address-space limits in the frozen policy
separately; this numerical driver does not impose OS limits itself. Full mode
executes 384 BE steps through 60 ps. Four atomic complete-field checkpoints,
every-step progress and a linear journal accompany the final JSON/NPZ record.

The report's derived oracle/guard files expose the unchanged physical checks
and reversible expected-ordering-label parameterization for inspection.
They require the recorded independent-auditor globals. The raw evidence path
in provenance retains the full audit script, its frozen input policy, results,
hash-linked parent evidence and archive receipt; derived files alone are not
standalone audit commands.
