#!/usr/bin/env python3
"""
Example: 3D PN junction simulation with visualization.
Generates PNG images for device structure and simulation results.
"""
import numpy as np
import sys
sys.path.insert(0, '/Users/yangfan/tcad')

import tcad
from tcad.viz.plotter import plot_device_geometry, plot_mesh_slice, plot_1d_cutline
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for saving PNG
import matplotlib.pyplot as plt

# ------------------------------------------------------------------
# 1. Build a 3D PN junction device
# ------------------------------------------------------------------
pn = tcad.Device.pnjunction(
    L=2e-6,        # Total length [m]
    W=1e-6,        # Width [m]
    H=1e-6,        # Height [m]
    x_junction=1e-6,
    Na=1e18,       # p-side doping [cm^-3]  (heavily doped)
    Nd=1e16,       # n-side doping [cm^-3]  (lightly doped)
)

# Save 3D device geometry wireframe
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

colors = plt.cm.tab10(np.linspace(0, 1, max(len(pn.regions), 1)))
for rid, region in enumerate(pn.regions):
    (xmin, xmax), (ymin, ymax), (zmin, zmax) = region.shape.bbox()
    verts = [
        [xmin, ymin, zmin], [xmax, ymin, zmin], [xmax, ymax, zmin], [xmin, ymax, zmin],
        [xmin, ymin, zmax], [xmax, ymin, zmax], [xmax, ymax, zmax], [xmin, ymax, zmax],
    ]
    faces = [
        [verts[0], verts[1], verts[2], verts[3]],
        [verts[4], verts[5], verts[6], verts[7]],
        [verts[0], verts[1], verts[5], verts[4]],
        [verts[2], verts[3], verts[7], verts[6]],
        [verts[1], verts[2], verts[6], verts[5]],
        [verts[0], verts[3], verts[7], verts[4]],
    ]
    ax.add_collection3d(Poly3DCollection(
        faces, facecolors=colors[rid % len(colors)], alpha=0.3, edgecolors="k", linewidths=0.5
    ))
    ax.text((xmin+xmax)/2, (ymin+ymax)/2, (zmin+zmax)/2, region.name, fontsize=7)

for name, (shape, voltage) in pn.contacts.items():
    (xmin, xmax), (ymin, ymax), (zmin, zmax) = shape.bbox()
    ax.plot([xmin, xmax, xmax, xmin, xmin], [ymin, ymin, ymax, ymax, ymin],
            [zmax, zmax, zmax, zmax, zmax], "r-", lw=2)
    ax.text((xmin+xmax)/2, (ymin+ymax)/2, zmax, f"{name}\n{voltage}V", color="red", fontsize=8)

ax.set_xlabel("x [m]")
ax.set_ylabel("y [m]")
ax.set_zlabel("z [m]")
ax.set_title(f"Device: {pn.name}")
plt.tight_layout()
plt.savefig("pn_device_geometry.png", dpi=150)
print("Saved: pn_device_geometry.png")
plt.close()

# ------------------------------------------------------------------
# 2. Generate mesh and simulate
# ------------------------------------------------------------------
mesh = tcad.generate_mesh(pn, method="structured", resolution=(20e-9, 100e-9, 100e-9))
print(f"Mesh size: {mesh.nx} x {mesh.ny} x {mesh.nz} = {mesh.npts()} nodes")

# Doping slice (before simulation)
fig, ax = plt.subplots(figsize=(8, 6))
nx, ny, nz = mesh.shape()
X, Y, Z = mesh.X, mesh.Y, mesh.Z
idx_z = nz // 2
xx, yy = X[:, :, idx_z], Y[:, :, idx_z]
slab = mesh.fields["doping"].reshape(nx, ny, nz)[:, :, idx_z]
extent = [xx.min(), xx.max(), yy.min(), yy.max()]
im = ax.imshow(slab.T, origin="lower", extent=extent, aspect="auto", cmap="RdBu_r")
fig.colorbar(im, ax=ax, label="Doping [cm^-3]")
ax.set_title(f"Doping profile (z = {Z[0,0,idx_z]:.3e} m)")
ax.set_xlabel("x [m]")
ax.set_ylabel("y [m]")
plt.tight_layout()
plt.savefig("pn_doping_slice.png", dpi=150)
print("Saved: pn_doping_slice.png")
plt.close()

# Run simulation
sim, results = tcad.simulate_device(pn, resolution=(20e-9, 100e-9, 100e-9),
                                     quantum=False, max_iter=50, tol=1e-8)
print(f"Converged: {results['converged']}, Iterations: {results['iterations']}")

# Attach results to mesh
fields = sim.to_mesh_fields()
for name, data in fields.items():
    mesh.add_field(name, data.ravel())

# ------------------------------------------------------------------
# 3. Visualize simulation results
# ------------------------------------------------------------------

# (a) Potential slice
fig, ax = plt.subplots(figsize=(8, 6))
slab_phi = mesh.fields["phi"].reshape(nx, ny, nz)[:, :, idx_z]
im = ax.imshow(slab_phi.T, origin="lower", extent=extent, aspect="auto", cmap="viridis")
fig.colorbar(im, ax=ax, label="Potential [V]")
ax.set_title(f"Electric Potential (z = {Z[0,0,idx_z]:.3e} m)")
ax.set_xlabel("x [m]")
ax.set_ylabel("y [m]")
plt.tight_layout()
plt.savefig("pn_potential_slice.png", dpi=150)
print("Saved: pn_potential_slice.png")
plt.close()

# (b) Electron concentration (log10)
fig, ax = plt.subplots(figsize=(8, 6))
log_n = np.log10(np.maximum(mesh.fields["n"].reshape(nx, ny, nz)[:, :, idx_z], 1e-10))
im = ax.imshow(log_n.T, origin="lower", extent=extent, aspect="auto", cmap="plasma")
fig.colorbar(im, ax=ax, label="log10(n) [m^-3]")
ax.set_title(f"Electron Concentration (z = {Z[0,0,idx_z]:.3e} m)")
ax.set_xlabel("x [m]")
ax.set_ylabel("y [m]")
plt.tight_layout()
plt.savefig("pn_electron_slice.png", dpi=150)
print("Saved: pn_electron_slice.png")
plt.close()

# (c) Hole concentration (log10)
fig, ax = plt.subplots(figsize=(8, 6))
log_p = np.log10(np.maximum(mesh.fields["p"].reshape(nx, ny, nz)[:, :, idx_z], 1e-10))
im = ax.imshow(log_p.T, origin="lower", extent=extent, aspect="auto", cmap="plasma")
fig.colorbar(im, ax=ax, label="log10(p) [m^-3]")
ax.set_title(f"Hole Concentration (z = {Z[0,0,idx_z]:.3e} m)")
ax.set_xlabel("x [m]")
ax.set_ylabel("y [m]")
plt.tight_layout()
plt.savefig("pn_hole_slice.png", dpi=150)
print("Saved: pn_hole_slice.png")
plt.close()

# (d) 1D cutline across junction
from scipy.interpolate import RegularGridInterpolator
x = np.linspace(mesh.xmin, mesh.xmax, nx)
y = np.linspace(mesh.ymin, mesh.ymax, ny)
z = np.linspace(mesh.zmin, mesh.zmax, nz)

phi_interp = RegularGridInterpolator((x, y, z), fields["phi"].reshape(nx, ny, nz), bounds_error=False, fill_value=0.0)
n_interp = RegularGridInterpolator((x, y, z), fields["n"].reshape(nx, ny, nz), bounds_error=False, fill_value=0.0)
p_interp = RegularGridInterpolator((x, y, z), fields["p"].reshape(nx, ny, nz), bounds_error=False, fill_value=0.0)

t = np.linspace(0, 1, 200)
xs = 0 + t * (2e-6 - 0)
ys = 0.5e-6 * np.ones_like(t)
zs = 0.5e-6 * np.ones_like(t)
pts = np.column_stack((xs, ys, zs))
dist = xs

fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
axes[0].plot(dist, phi_interp(pts), "b-")
axes[0].set_ylabel("Potential [V]")
axes[0].set_title("1D Cutline across PN junction")
axes[0].grid(True)

axes[1].semilogy(dist, n_interp(pts), "r-", label="n")
axes[1].semilogy(dist, p_interp(pts), "g-", label="p")
axes[1].set_ylabel("Carrier density [m^-3]")
axes[1].legend()
axes[1].grid(True)

axes[2].plot(dist, n_interp(pts) - p_interp(pts), "k-")
axes[2].set_ylabel("n - p [m^-3]")
axes[2].set_xlabel("x [m]")
axes[2].grid(True)

plt.tight_layout()
plt.savefig("pn_1d_cutline.png", dpi=150)
print("Saved: pn_1d_cutline.png")
plt.close()

# Save VTK for ParaView
sim.save("pn_junction_result.vtu")
print("Saved: pn_junction_result.vtu")
print("\nAll visualization files generated successfully!")
