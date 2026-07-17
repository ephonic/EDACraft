#!/usr/bin/env python3
"""
可视化示例：1D PN 结仿真结果展示
当前 Newton 求解器在细网格 3D 问题上收敛较慢，
这里先用 1D 网格展示物理正确的结果和可视化能力。
"""
import numpy as np
import sys
sys.path.insert(0, '/Users/yangfan/tcad')

from tcad.core import PyDeviceSimulator as DeviceSimulator
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# ------------------------------------------------------------------
# 1. 1D PN 结仿真（5 节点，收敛快且稳定）
# ------------------------------------------------------------------
N = 5
dx = 1e-9
sim = DeviceSimulator(N, 1, 1, dx, dx, dx)

doping = np.ones(N) * 1e22
doping[:2] = -1e24   # p-side
doping[2:] = 1e22    # n-side
sim.set_doping(doping)

VT = 0.02585
ni = 1e16
phi_n = VT * np.log(1e22 / ni)   # ~0.357 V
phi_p = -VT * np.log(1e24 / ni)  # ~-0.476 V

sim.set_dirichlet_potential({0: phi_p, N-1: phi_n})
sim.set_electron_bc({0: 1e8, N-1: 1e22})
sim.set_hole_bc({0: 1e24, N-1: 1e10})
sim.set_gummel_max_iter(50)
sim.set_tolerance(1e-8)

res = sim.solve()
print(f"Converged: {res['converged']}, Iterations: {res['iterations']}")

phi = res['phi']
n_arr = res['n']
p_arr = res['p']
x = np.arange(N) * dx

# ------------------------------------------------------------------
# 2. 3D 器件结构示意图（matplotlib 线框）
# ------------------------------------------------------------------
fig = plt.figure(figsize=(10, 6))
ax = fig.add_subplot(111, projection='3d')

L = (N - 1) * dx
W = H = dx
x_j = 1.5 * dx  # junction position

# p-side
verts_p = [
    [0, 0, 0], [x_j, 0, 0], [x_j, W, 0], [0, W, 0],
    [0, 0, H], [x_j, 0, H], [x_j, W, H], [0, W, H],
]
faces_p = [
    [verts_p[0], verts_p[1], verts_p[2], verts_p[3]],
    [verts_p[4], verts_p[5], verts_p[6], verts_p[7]],
    [verts_p[0], verts_p[1], verts_p[5], verts_p[4]],
    [verts_p[2], verts_p[3], verts_p[7], verts_p[6]],
    [verts_p[1], verts_p[2], verts_p[6], verts_p[5]],
    [verts_p[0], verts_p[3], verts_p[7], verts_p[4]],
]
ax.add_collection3d(Poly3DCollection(
    faces_p, facecolors='steelblue', alpha=0.4, edgecolors='k', linewidths=0.5
))
ax.text(x_j/2, W/2, H/2, 'p-side\nNa=1e18 cm⁻³', fontsize=9, ha='center')

# n-side
verts_n = [
    [x_j, 0, 0], [L, 0, 0], [L, W, 0], [x_j, W, 0],
    [x_j, 0, H], [L, 0, H], [L, W, H], [x_j, W, H],
]
faces_n = [
    [verts_n[0], verts_n[1], verts_n[2], verts_n[3]],
    [verts_n[4], verts_n[5], verts_n[6], verts_n[7]],
    [verts_n[0], verts_n[1], verts_n[5], verts_n[4]],
    [verts_n[2], verts_n[3], verts_n[7], verts_n[6]],
    [verts_n[1], verts_n[2], verts_n[6], verts_n[5]],
    [verts_n[0], verts_n[3], verts_n[7], verts_n[4]],
]
ax.add_collection3d(Poly3DCollection(
    faces_n, facecolors='coral', alpha=0.4, edgecolors='k', linewidths=0.5
))
ax.text((x_j+L)/2, W/2, H/2, 'n-side\nNd=1e16 cm⁻³', fontsize=9, ha='center')

# Contacts
ax.plot([0, 0], [0, W], [0, 0], 'r-', lw=3, label='p-contact (φ=-0.476V)')
ax.plot([L, L], [0, W], [0, 0], 'g-', lw=3, label='n-contact (φ=+0.357V)')

ax.set_xlabel('x [m]')
ax.set_ylabel('y [m]')
ax.set_zlabel('z [m]')
ax.set_title('PN Junction Device Structure (3D schematic)')
ax.legend()
plt.tight_layout()
plt.savefig('pn_3d_structure.png', dpi=150)
print('Saved: pn_3d_structure.png')
plt.close()

# ------------------------------------------------------------------
# 3. 1D 仿真结果图
# ------------------------------------------------------------------
fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

axes[0].plot(x * 1e9, phi, 'b-o', markersize=6, label='φ')
axes[0].axvline(x_j * 1e9, color='k', linestyle='--', alpha=0.5, label='junction')
axes[0].set_ylabel('Potential [V]')
axes[0].set_title('PN Junction Simulation Results (1D cutline)')
axes[0].legend()
axes[0].grid(True)

axes[1].semilogy(x * 1e9, n_arr, 'r-o', markersize=6, label='n (electrons)')
axes[1].semilogy(x * 1e9, p_arr, 'g-s', markersize=6, label='p (holes)')
axes[1].semilogy(x * 1e9, np.abs(doping), 'k--', alpha=0.5, label='|Nd-Na|')
axes[1].axvline(x_j * 1e9, color='k', linestyle='--', alpha=0.5)
axes[1].set_ylabel('Density [m⁻³]')
axes[1].set_xlabel('x [nm]')
axes[1].legend()
axes[1].grid(True)

plt.tight_layout()
plt.savefig('pn_1d_results.png', dpi=150)
print('Saved: pn_1d_results.png')
plt.close()

# ------------------------------------------------------------------
# 4. 电势/载流子空间分布热图（将 1D 结果扩展为伪 2D 切片）
# ------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(15, 4))

# 将 1D 结果复制到 2D 平面用于可视化
ny_vis = 20
phi_2d = np.tile(phi, (ny_vis, 1))
n_2d = np.tile(n_arr, (ny_vis, 1))
p_2d = np.tile(p_arr, (ny_vis, 1))

im0 = axes[0].imshow(phi_2d, origin='lower', extent=[0, L*1e9, 0, 1], aspect='auto', cmap='viridis')
axes[0].set_title('Potential [V]')
axes[0].set_xlabel('x [nm]')
fig.colorbar(im0, ax=axes[0])

im1 = axes[1].imshow(np.log10(n_2d), origin='lower', extent=[0, L*1e9, 0, 1], aspect='auto', cmap='plasma')
axes[1].set_title('log₁₀(n) [m⁻³]')
axes[1].set_xlabel('x [nm]')
fig.colorbar(im1, ax=axes[1])

im2 = axes[2].imshow(np.log10(p_2d), origin='lower', extent=[0, L*1e9, 0, 1], aspect='auto', cmap='plasma')
axes[2].set_title('log₁₀(p) [m⁻³]')
axes[2].set_xlabel('x [nm]')
fig.colorbar(im2, ax=axes[2])

plt.suptitle('Pseudo-2D Slice Visualization (1D result extruded in y)', fontsize=12)
plt.tight_layout()
plt.savefig('pn_2d_slices.png', dpi=150)
print('Saved: pn_2d_slices.png')
plt.close()

print('\nAll visualization files generated successfully!')
