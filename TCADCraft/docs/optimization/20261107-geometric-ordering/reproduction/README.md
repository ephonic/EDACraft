# Replay the captured matrix

Install the matching development sources and a compatible SI float128 native
build. The tested environment used Python 3.13.5, NumPy 2.1.3 and SciPy 1.15.3.
Native and source hashes are in [provenance](../PROVENANCE.json).

From the TCADCraft project root, run in a fresh process with one thread:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONNOUSERSITE=1 TCAD_EXPECT_PRECISION=float128 TCAD_EXPECT_CONSTANTS_PROFILE=si \
  python -B docs/optimization/20261107-geometric-ordering/reproduction/product_matrix.py \
  docs/optimization/20261107-geometric-ordering/data/first_DC_matrix.npz \
  /tmp/geometric-matrix-replay.json
```

The script writes JSON and a solution/permutation NPZ, checking the true
original-matrix max norm at 1e-14. Apply the recorded 900 s wall/CPU,
48 GiB address-space and 32 GiB peak-RSS limits separately; the matrix script
does not install OS limits itself. This is one linear solve, not a device run.
The included accepted solution supports independent CSR row-sum replay with
NumPy alone. Source fixture SHA and the original result are recorded in
[integrated verification](../integration_verification.json).

To replay the targeted tests from the project root:

```bash
python -B -m pytest -q -p no:cacheprovider \
  tests/test_sheet_linear_cache_release.py tests/test_sheet_reused_gmres.py \
  tests/test_sheet_linear_ordering.py tests/test_sheet_coupled.py \
  tests/test_sheet_dielectric_contacts.py tests/test_sheet_transient.py \
  tests/test_sheet_geometric_ordering.py
```

The frozen [integration policy](../integration_policy.json) identifies exact
sources, native binary, threads, limits and expected 245 tests.

For a fresh observational capture, create a workspace with `input/` and
`artifacts/`. Copy this directory's independent_y2_probe.py, meshes.npz,
sheet_runtime_profile_20261106.py, sheet_electrode_convergence.py and
sheet_trap_convergence.py into `input/`, plus capture_matrix.py. With the
recorded original sources/native environment and the same limits, invoke
`python -B WORK/input/capture_matrix.py WORK`. It captures the original first
DC matrix then stops; it never completes or accepts a device state. The
original capture policy is preserved in [capture_policy.json](../capture_policy.json).
