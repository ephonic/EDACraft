# Replay explicit post-DC cache release

Use the development sources with `SheetTransient.clear_linear_cache()` and a
working SI float128 native extension. From the TCADCraft root:

```bash
mkdir -p /tmp/tcad-cache-release-replay
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONPATH=.:benchmarks python \
  docs/optimization/20261106-linear-cache-release/reproduction/independent_y1_probe.py \
  thermionic space 3 128 probe /tmp/tcad-cache-release-replay/y17
```

Keep `meshes.npz` beside the driver. Its only change from the sealed baseline
is `assert run.clear_linear_cache()` after saving the initial checkpoint.
The recorded attempt timed out at 1,800 s without completing the first BE step.
These shell commands do not impose that timeout, the 16 GiB address-space
limit or 6 GiB peak-RSS acceptance gate. Declare resource limits before a new
comparison and supervise the serial process. Atomic exports are diagnostics,
not restart files. Representative material parameters remain uncalibrated.
