# Replay the temporal pulse and endpoint probes

Use the built development checkout with optional MMD ordering and its working
native extension. From the TCADCraft root:

```bash
mkdir -p /tmp/tcad-temporal-endpoint-replay
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONPATH=.:benchmarks python \
  docs/optimization/20261106-temporal-endpoint/reproduction/local_z1_n512.py \
  thermionic space 3 512 full /tmp/tcad-temporal-endpoint-replay/local_z1_n512
```

For a probe, choose `endpoint_z1_probe.py`, `endpoint_z2_probe.py` or
`endpoint_x1_probe.py`, use `128 probe` instead of `512 full`, and give it a
distinct output stem. Keep all scripts beside `meshes.npz`. Legacy `space 3`
arguments are retained; exact nonuniform geometry comes from each frozen driver.
They are not a uniform global spatial-refinement family.

The retry runner applied 4,800 s for the full pulse, 900 s per probe, 16 GiB
address space and a 6 GiB peak-RSS ceiling. These replay commands do not impose
those limits. Run serially on a suitable host and supervise resource use.
Atomic checkpoints preserve diagnostic evidence; they are not restart files.

Given same-mesh 128/256/512 result stems, compare three complete traces with:

```bash
python benchmarks/sheet_refinement_trace.py COARSE_STEM FINE_STEM \
  --middle MIDDLE_STEM --output three_time_trace.json
```

The original two-stem command remains available without `--middle`. Results
report numerical differences and observed orders, not physical qualification.
