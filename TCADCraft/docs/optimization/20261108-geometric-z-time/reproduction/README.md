# Reproduce the four z/time controls

Use the numerical source and SI float128 native extension identified in
[provenance](../PROVENANCE.json). Keep drivers, meshes.npz and helper modules
together. Run serially with the precision/thread environment and resource
limits from [policy](../policy.json), from the TCADCraft root:

```bash
python -B docs/optimization/20261108-geometric-z-time/reproduction/geometric_z121_n128.py thermionic space 3 128 full /tmp/geometric_z121_n128
python -B docs/optimization/20261108-geometric-z-time/reproduction/geometric_z121_n256.py thermionic space 3 256 full /tmp/geometric_z121_n256
python -B docs/optimization/20261108-geometric-z-time/reproduction/geometric_z129_n128.py thermionic space 3 128 full /tmp/geometric_z129_n128
python -B docs/optimization/20261108-geometric-z-time/reproduction/geometric_z129_n256.py thermionic space 3 256 full /tmp/geometric_z129_n256
```

A fresh run must pass the same independent physical audit. Raw evidence
and parent-manifest identities are in provenance.
