# Replay the accepted contact-z/time cases

Use a built development checkout containing the optional MMD ordering and its
working native extension. From the TCADCraft root, keep this directory's scripts
beside `meshes.npz` and make the existing benchmark helpers importable:

```bash
mkdir -p /tmp/tcad-contact-z-replay
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONPATH=.:benchmarks python \
  docs/optimization/20261106-contact-z-time/reproduction/local_z2_n128.py \
  thermionic space 3 128 full /tmp/tcad-contact-z-replay/local_z2_n128
```

The other two frozen commands use `local_z1_n256.py` / `local_z2_n256.py`, with
`256` instead of `128` and distinct output stems. Run serially. The original
runner imposed 1,800 seconds per case, 16 GiB address space and a 6 GiB peak-RSS
acceptance ceiling; these shell commands do not impose those limits themselves.
Choose a host able to run the original case and supervise long runs accordingly.

Each output stem produces JSON/NPZ full results, per-step progress and linear
records, accepted-linear JSONL and atomic initial/phase-end field exports.
The final stdout JSON reports steps, residual, elapsed time and process peak RSS.
Solver acceptance alone does not replace the independent physical audit.

The legacy `space 3` command arguments are retained from the original driver.
The exact nonuniform local-z mesh comes from this directory's frozen
`meshes.npz` and the selected script; these outputs are not a uniform global
space-refinement family.

After generating same-mesh coarse/fine records, compare complete traces with:

```bash
python benchmarks/sheet_refinement_trace.py \
  /tmp/tcad-contact-z-replay/local_z2_n128 \
  /tmp/tcad-contact-z-replay/local_z2_n256 \
  --output /tmp/tcad-contact-z-replay/local_z2_time_comparison.json
```

Total BE currents are compared after averaging fine substeps over each coarse
physical interval. Ending-time conduction currents and cumulative signed charge
are also reported. The output is descriptive and sets no acceptance threshold.
