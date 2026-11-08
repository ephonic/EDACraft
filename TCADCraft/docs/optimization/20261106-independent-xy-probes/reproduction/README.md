# Replay independent x/y probes

Use the built development checkout with optional MMD ordering and its working
native extension. From the TCADCraft root:

```bash
mkdir -p /tmp/tcad-xy-probe-replay
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONPATH=.:benchmarks python \
  docs/optimization/20261106-independent-xy-probes/reproduction/endpoint_x3_probe.py \
  thermionic space 3 128 probe /tmp/tcad-xy-probe-replay/endpoint_x3_probe
```

Repeat with `independent_y1_probe.py` and a distinct output stem. Keep drivers
beside `meshes.npz`. Legacy `space 3` arguments remain; exact nonuniform x/y/z
coordinates come from the frozen drivers rather than global refinement.

The runner imposed 900/1,800 s for x/y, 16 GiB address space and 6 GiB peak RSS.
The y17 case exceeded the frozen RSS budget and was rejected by the worker;
its completed fields are diagnostic evidence only. These commands do not
impose those limits. Run serially and supervise resources.
Atomic exports are diagnostic evidence, not restart files. Physical parameters
remain representative and uncalibrated.
