#!/usr/bin/env python3
"""
3D MOSFET simulation with tcad.

This demonstrates the full 3D capability using the high-level Simulator API.
The device has finite width W in the z-direction, requiring nz > 1.

Usage:
    python examples/mosfet_3d.py
"""

import numpy as np
import matplotlib.pyplot as plt
from tcad import simulate_device, Device

# Device parameters (meters)
Lg = 50e-9      # Gate length
tox = 1.5e-9    # Oxide thickness
tsi = 10e-9     # Silicon thickness
W = 40e-9       # Width (z-direction) — THIS IS THE 3D DIMENSION
Lsd = 25e-9     # Source/Drain extension length
Vg = 0.3        # Gate voltage
Vd = 0.1        # Drain voltage
Vs = 0.0        # Source voltage

# Mesh resolution
dx = 5e-9
dy = 2e-9
dz = 10e-9

print(f"Building 3D MOSFET: Lg={Lg*1e9:.0f}nm, tsi={tsi*1e9:.0f}nm, W={W*1e9:.0f}nm")

# Build device geometry
device = Device.mosfet(Lg=Lg, tox=tox, tsi=tsi, W=W, Lsd=Lsd, Vg=Vg, Vd=Vd, Vs=Vs)

# Run simulation
sim, results = simulate_device(
    device,
    resolution=(dx, dy, dz),
    temperature=300.0,
    quantum=False,
    max_iter=100,
    tol=1e-8,
)

print(f"3D MOSFET converged={results['converged']}, iters={results['iterations']}")
print(f"Grid shape: {sim.mesh.shape()}")

# Extract and visualize a center z-slice
nx, ny, nz = sim.mesh.shape()
phi_3d = results['phi'].reshape(nx, ny, nz)
n_3d = results['n'].reshape(nx, ny, nz)
p_3d = results['p'].reshape(nx, ny, nz)

# Take slice at z = W/2 (middle of width)
z_idx = nz // 2
phi_slice = phi_3d[:, :, z_idx].T
n_slice = n_3d[:, :, z_idx].T
p_slice = p_3d[:, :, z_idx].T

x = np.linspace(0, 2*Lsd + Lg, nx) * 1e9
y = np.linspace(0, tsi + tox + 10e-9, ny) * 1e9

fig, axes = plt.subplots(1, 3, figsize=(15, 4))

ax = axes[0]
im = ax.pcolormesh(x, y, phi_slice, shading='auto', cmap='RdBu_r')
ax.set_title(f"Potential (Vg={Vg}V, Vd={Vd}V)")
ax.set_xlabel('x [nm]')
ax.set_ylabel('y [nm]')
plt.colorbar(im, ax=ax)

ax = axes[1]
im = ax.pcolormesh(x, y, np.log10(np.clip(n_slice, 1e10, 1e25)), shading='auto', cmap='viridis', vmin=10, vmax=25)
ax.set_title('log10(n)')
ax.set_xlabel('x [nm]')
ax.set_ylabel('y [nm]')
plt.colorbar(im, ax=ax)

ax = axes[2]
im = ax.pcolormesh(x, y, np.log10(np.clip(p_slice, 1e10, 1e25)), shading='auto', cmap='plasma', vmin=10, vmax=25)
ax.set_title('log10(p)')
ax.set_xlabel('x [nm]')
ax.set_ylabel('y [nm]')
plt.colorbar(im, ax=ax)

plt.tight_layout()
plt.savefig('mosfet_3d_slice.png', dpi=150)
print("Saved center slice to mosfet_3d_slice.png")

# Id-Vg sweep (simplified: reuse same device, vary gate voltage)
print("\n--- Id-Vg sweep ---")
for vg in [0.0, 0.1, 0.2, 0.3, 0.4]:
    dev = Device.mosfet(Lg=Lg, tox=tox, tsi=tsi, W=W, Lsd=Lsd, Vg=vg, Vd=Vd, Vs=Vs)
    s, r = simulate_device(dev, resolution=(dx, dy, dz), quantum=False, max_iter=100, tol=1e-8)
    if r['converged']:
        # Approximate drain current from electron density gradient at drain
        n_3d = r['n'].reshape(nx, ny, nz)
        # Simple estimate: average n at drain contact * mobility * E-field
        # For demonstration, just report max n in channel
        n_max = n_3d.max()
        print(f"Vg={vg:.1f}V: converged in {r['iterations']} iters, n_max={n_max:.3e}")
    else:
        print(f"Vg={vg:.1f}V: DID NOT CONVERGE")
