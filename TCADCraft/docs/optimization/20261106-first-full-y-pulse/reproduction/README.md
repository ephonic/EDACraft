# Replay the complete y17 pulse

Use sources with `SheetTransient.clear_linear_cache()` and a working Linux
SI float128 native extension. From the TCADCraft root:

```bash
mkdir -p /tmp/tcad-y17-replay
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONPATH=.:benchmarks python \
  docs/optimization/20261106-first-full-y-pulse/reproduction/independent_y1_full.py \
  thermionic space 3 128 full /tmp/tcad-y17-replay/y17
```

Keep the exact `meshes.npz` beside the driver. Enforce the separate recorded
3,600 s / 16 GiB AS / 6 GiB peak-RSS budgets. Atomic field exports are
diagnostic checkpoints rather than restart files. All 384 steps are rerun.
