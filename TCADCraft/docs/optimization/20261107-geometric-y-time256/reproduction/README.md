# Replay the two half-dt controls

Use the numerical source and SI float128 native extension identified in
[provenance](../PROVENANCE.json). Keep each driver, meshes.npz and both helper
modules together. From the TCADCraft root, run each command serially with the
thread limits and precision environment from policy:

```bash
python -B docs/optimization/20261107-geometric-y-time256/reproduction/geometric_y9_n256.py thermionic space 3 256 full /tmp/y9-n256
python -B docs/optimization/20261107-geometric-y-time256/reproduction/geometric_y17_n256.py thermionic space 3 256 full /tmp/y17-n256
```

Set OPENBLAS_NUM_THREADS=1, OMP_NUM_THREADS=1, MKL_NUM_THREADS=1,
PYTHONNOUSERSITE=1, TCAD_EXPECT_PRECISION=float128 and
TCAD_EXPECT_CONSTANTS_PROFILE=si. Enforce wall/CPU/RSS/address-space budgets
separately; drivers impose no OS limits. The sealed raw directory retains the
full numerical outputs, scripts, source identities and receipt. Derived oracle
functions need the recorded globals and are not standalone CLI programs.
Use the original metric function and diagnostic acceptance policy on all three
y grids at n256. For signed interactions, the analysis helper projects fields
onto the coarsest nested support before combining the four corners.
