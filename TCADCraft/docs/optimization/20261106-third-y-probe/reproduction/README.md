# Reproduce the bounded probes

Use the exact source and SI float128 native identities in provenance.
From the TCADCraft root, with `meshes.npz` beside both drivers:

```bash
mkdir -p /tmp/tcad-uniform-y-replay
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=.:benchmarks python docs/optimization/20261106-third-y-probe/reproduction/independent_y0_probe.py thermionic space 3 128 probe /tmp/tcad-uniform-y-replay/y9
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=.:benchmarks python docs/optimization/20261106-third-y-probe/reproduction/independent_y2_probe.py thermionic space 3 128 probe /tmp/tcad-uniform-y-replay/y33
```

Enforce the case-specific wall/CPU, address-space and RSS limits from
`policy.json`. The recorded y33 outcome is a failure under that policy.
These are one-step drivers; saved checkpoints are not restart files.
