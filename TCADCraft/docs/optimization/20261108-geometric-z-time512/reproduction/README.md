# Reproduce the two fresh n512 pulses

Use the source/native identities in [provenance](../PROVENANCE.json), keeping
drivers, meshes.npz and helper modules together. From the TCADCraft root:

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONNOUSERSITE=1 TCAD_EXPECT_PRECISION=float128 TCAD_EXPECT_CONSTANTS_PROFILE=si
python -B docs/optimization/20261108-geometric-z-time512/reproduction/geometric_z113_n512.py thermionic space 3 512 full /tmp/geometric_z113_n512
python -B docs/optimization/20261108-geometric-z-time512/reproduction/geometric_z121_n512.py thermionic space 3 512 full /tmp/geometric_z121_n512
```

Enforce [policy](../policy.json) wall/CPU/RSS/address-space limits separately;
the driver imposes no OS limits. Run serially and apply the same independent
audit to all steps. The other seven sealed corners and exact comparator identities
are listed in provenance. Raw evidence includes complete artifacts and scripts.
