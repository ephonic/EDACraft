# Replay endpoint full pulses and the second x probe

Use the built development checkout with optional MMD ordering and its working
native extension. From the TCADCraft root:

```bash
mkdir -p /tmp/tcad-endpoint-full-replay
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONPATH=.:benchmarks python \
  docs/optimization/20261106-endpoint-full/reproduction/endpoint_z1_n128.py \
  thermionic space 3 128 full /tmp/tcad-endpoint-full-replay/endpoint_z1_n128
```

Repeat with `endpoint_z2_n128.py` and a distinct output stem. For the x probe,
choose `endpoint_x2_probe.py` and replace `128 full` with `128 probe`. Keep the
drivers beside `meshes.npz`. Legacy `space 3` arguments remain; the exact nested
nonuniform coordinates come from each frozen driver, not uniform refinement.

The runner imposed 4,800 s per full pulse, 900 s for the probe, 16 GiB address
space and a 6 GiB peak-RSS ceiling. These commands do not impose those limits.
Run serially and supervise resources. Atomic exports are diagnostic evidence,
not restart files. Representative physical parameters remain uncalibrated.
