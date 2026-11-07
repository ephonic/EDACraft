# Reproduce the two x69 controls

Use the numerical source and SI float128 native extension identified in
[provenance](../PROVENANCE.json). Keep both drivers, meshes.npz and helper
modules together. Run serially with the precision/thread environment and
resource limits from [policy](../policy.json), from the TCADCraft root:

```bash
python -B docs/optimization/20261107-geometric-x-time/reproduction/geometric_x69_n128.py thermionic space 3 128 full /tmp/x69-n128
python -B docs/optimization/20261107-geometric-x-time/reproduction/geometric_x69_n256.py thermionic space 3 256 full /tmp/x69-n256
```

A fresh run must pass the same independent audit; exit status alone is not
acceptance. Raw evidence and parent-manifest identities are in provenance.
