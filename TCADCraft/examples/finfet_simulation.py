#!/usr/bin/env python3
"""
FinFET 3D simulation and visualization.

Demonstrates:
  1. FinFET device construction
  2. 3D structured mesh generation
  3. Self-consistent Gummel solve
  4. 2D slice + 3D scatter visualization via matplotlib

Usage:
    python examples/finfet_simulation.py
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device

# ------------------------------------------------------------------
# Device parameters (meters)
# ------------------------------------------------------------------
Lg = 30e-9      # Gate length
tox = 1.5e-9    # Oxide thickness
tsi = 10e-9     # Fin thickness (y-direction)
Hfin = 30e-9    # Fin height (z-direction)
Lsd = 30e-9     # Source/Drain extension
tgate = 10e-9   # Gate metal thickness
Vg = 0.7        # Gate voltage
Vd = 0.1        # Drain voltage
Vs = 0.0        # Source voltage

print(f"Building FinFET: Lg={Lg*1e9:.0f}nm, tsi={tsi*1e9:.0f}nm, Hfin={Hfin*1e9:.0f}nm")

# Build FinFET geometry
device = Device.finfet(
    Lg=Lg, tox=tox, tsi=tsi, Hfin=Hfin,
    Lsd=Lsd, tgate=tgate, Vg=Vg, Vd=Vd, Vs=Vs,
)

# Mesh resolution — finer in y (fin thickness) for accuracy
dx = 5e-9
dy = 2.5e-9
dz = 5e-9

mesh = structured_mesh_from_device(device, resolution=(dx, dy, dz))
print(f"Grid: {mesh.nx} x {mesh.ny} x {mesh.nz} = {mesh.nx*mesh.ny*mesh.nz} nodes")

# Run simulation
sim = Simulator(mesh, temperature=300.0)
sim.set_material_from_mesh()
for name, (shape, voltage) in device.contacts.items():
    sim.set_contact(name, voltage)

results = sim.run(max_iter=120, tol=1e-8)
print(f"Converged={results['converged']}, iters={results['iterations']}")

# ------------------------------------------------------------------
# Reshape results to 3D
# ------------------------------------------------------------------
phi = results['phi'].reshape(mesh.nx, mesh.ny, mesh.nz)
n = results['n'].reshape(mesh.nx, mesh.ny, mesh.nz)
p = results['p'].reshape(mesh.nx, mesh.ny, mesh.nz)

# Coordinate arrays
x = np.linspace(0, mesh.dx * (mesh.nx - 1), mesh.nx) * 1e9  # nm
y = np.linspace(0, mesh.dy * (mesh.ny - 1), mesh.ny) * 1e9
z = np.linspace(0, mesh.dz * (mesh.nz - 1), mesh.nz) * 1e9

# ------------------------------------------------------------------
# Figure 1: 2D slices (potential + carriers)
# ------------------------------------------------------------------
fig, axes = plt.subplots(2, 3, figsize=(15, 9))

# Find slices that cut through the FIN (not the oxide/metal)
# Fin occupies y in [0, tsi] and z in [0, Hfin]
mid_x = mesh.nx // 2
mid_y = np.argmin(np.abs(y - tsi * 1e9 / 2))  # fin center in y
mid_z = np.argmin(np.abs(z - Hfin * 1e9 / 2))  # fin center in z

# --- phi slices ---
ax = axes[0, 0]
im = ax.pcolormesh(x, y, phi[:, :, mid_z].T, shading='auto', cmap='RdBu_r')
ax.set_title(f'Potential φ  (z={z[mid_z]:.1f}nm)')
ax.set_xlabel('x [nm]'); ax.set_ylabel('y [nm]')
plt.colorbar(im, ax=ax)

ax = axes[0, 1]
im = ax.pcolormesh(x, z, phi[:, mid_y, :].T, shading='auto', cmap='RdBu_r')
ax.set_title(f'Potential φ  (y={y[mid_y]:.1f}nm)')
ax.set_xlabel('x [nm]'); ax.set_ylabel('z [nm]')
plt.colorbar(im, ax=ax)

ax = axes[0, 2]
im = ax.pcolormesh(y, z, phi[mid_x, :, :].T, shading='auto', cmap='RdBu_r')
ax.set_title(f'Potential φ  (x={x[mid_x]:.1f}nm, gate center)')
ax.set_xlabel('y [nm]'); ax.set_ylabel('z [nm]')
plt.colorbar(im, ax=ax)

# --- log10(n) slices ---
ax = axes[1, 0]
n_clip = np.clip(n[:, :, mid_z], 1e10, None)
im = ax.pcolormesh(x, y, np.log10(n_clip.T), shading='auto', cmap='viridis')
ax.set_title(f'log₁₀(n)  (z={z[mid_z]:.1f}nm)')
ax.set_xlabel('x [nm]'); ax.set_ylabel('y [nm]')
plt.colorbar(im, ax=ax)

ax = axes[1, 1]
n_clip = np.clip(n[:, mid_y, :], 1e10, None)
im = ax.pcolormesh(x, z, np.log10(n_clip.T), shading='auto', cmap='viridis')
ax.set_title(f'log₁₀(n)  (y={y[mid_y]:.1f}nm)')
ax.set_xlabel('x [nm]'); ax.set_ylabel('z [nm]')
plt.colorbar(im, ax=ax)

ax = axes[1, 2]
n_clip = np.clip(n[mid_x, :, :], 1e10, None)
im = ax.pcolormesh(y, z, np.log10(n_clip.T), shading='auto', cmap='viridis')
ax.set_title(f'log₁₀(n)  (x={x[mid_x]:.1f}nm)')
ax.set_xlabel('y [nm]'); ax.set_ylabel('z [nm]')
plt.colorbar(im, ax=ax)

plt.suptitle(f'FinFET 3D Simulation  (Vg={Vg}V, Vd={Vd}V)')
plt.tight_layout()
plt.savefig('finfet_slices.png', dpi=150)
print("Saved 2D slices to finfet_slices.png")

# ------------------------------------------------------------------
# Figure 2: 3D scatter (electron concentration)
# ------------------------------------------------------------------
fig = plt.figure(figsize=(12, 5))

# Subsample for clarity
stride = max(1, min(mesh.nx, mesh.ny, mesh.nz) // 12)

ax1 = fig.add_subplot(121, projection='3d')
# Plot electron density as colored scatter
n_log = np.log10(np.clip(n[::stride, ::stride, ::stride], 1e10, None))
points = np.meshgrid(x[::stride], y[::stride], z[::stride], indexing='ij')
ax1.scatter(points[0].ravel(), points[1].ravel(), points[2].ravel(),
            c=n_log.ravel(), cmap='viridis', s=20, alpha=0.6)
ax1.set_xlabel('x [nm]')
ax1.set_ylabel('y [nm]')
ax1.set_zlabel('z [nm]')
ax1.set_title('3D Electron Density (log₁₀ n)')

ax2 = fig.add_subplot(122, projection='3d')
phi_sub = phi[::stride, ::stride, ::stride]
ax2.scatter(points[0].ravel(), points[1].ravel(), points[2].ravel(),
            c=phi_sub.ravel(), cmap='RdBu_r', s=20, alpha=0.6)
ax2.set_xlabel('x [nm]')
ax2.set_ylabel('y [nm]')
ax2.set_zlabel('z [nm]')
ax2.set_title('3D Potential φ [V]')

plt.tight_layout()
plt.savefig('finfet_3d.png', dpi=150)
print("Saved 3D scatter to finfet_3d.png")

# ------------------------------------------------------------------
# Quick stats
# ------------------------------------------------------------------
print(f"\n--- Results ---")
print(f"φ range: [{phi.min():.3f}, {phi.max():.3f}] V")
print(f"n max: {n.max():.3e} m⁻³")
print(f"p max: {p.max():.3e} m⁻³")
print(f"Inversion n at gate center (x={x[mid_x]:.1f}nm): {n[mid_x, mid_y, mid_z]:.3e}")
