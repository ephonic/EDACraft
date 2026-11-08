# Replay the profiled y17 probe

Use the development sources with `SheetTransient.clear_linear_cache()` and
a working Linux SI float128 native extension. From the TCADCraft root:

```bash
mkdir -p /tmp/tcad-profile-replay
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONPATH=.:benchmarks python \
  docs/optimization/20261106-cache-profile/reproduction/independent_y1_probe.py \
  thermionic space 3 128 probe /tmp/tcad-profile-replay/y17
```

Keep the exact `meshes.npz` and `sheet_runtime_profile_20261106.py` beside
the driver. The `.profile.jsonl` file records nested timing events separately
from physical exports. The commands do not impose the recorded 3,600 s / 16 GiB
address-space / 6 GiB peak-RSS budgets; declare limits and supervise the serial
run separately. Atomic exports are diagnostics, not restart files.
