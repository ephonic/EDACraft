# Replay the complete x75 and x83 pulses

Use sources with `SheetTransient.clear_linear_cache()` and a working Linux
SI float128 native extension. From the TCADCraft root, run the cases serially:

```bash
mkdir -p /tmp/tcad-x-sequence
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONPATH=.:benchmarks python \
  docs/optimization/20261106-full-x-sequence/reproduction/endpoint_x2_full.py \
  thermionic space 3 128 full /tmp/tcad-x-sequence/x75
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONPATH=.:benchmarks python \
  docs/optimization/20261106-full-x-sequence/reproduction/endpoint_x3_full.py \
  thermionic space 3 128 full /tmp/tcad-x-sequence/x83
```

Keep the exact `meshes.npz` beside both drivers. Declare and supervise the
3,600 s / 16 GiB AS / 6 GiB peak-RSS limits per case separately. Each driver
executes all 384 steps. Atomic exports are diagnostics rather than restart files.
