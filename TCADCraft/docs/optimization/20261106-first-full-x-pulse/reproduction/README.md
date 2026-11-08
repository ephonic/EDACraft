# Replay the complete x69 pulse

Use sources with `SheetTransient.clear_linear_cache()` and a working Linux
SI float128 native extension. From the TCADCraft root:

```bash
mkdir -p /tmp/tcad-x69-replay
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONPATH=.:benchmarks python \
  docs/optimization/20261106-first-full-x-pulse/reproduction/endpoint_x1_full.py \
  thermionic space 3 128 full /tmp/tcad-x69-replay/x69
```

Keep the exact `meshes.npz` beside the driver. Declare and supervise the
recorded 3,600 s / 16 GiB AS / 6 GiB peak-RSS limits separately. Atomic exports
are diagnostic checkpoints rather than restart files. The driver executes
all 384 steps; it does not resume from the inherited short probe.
