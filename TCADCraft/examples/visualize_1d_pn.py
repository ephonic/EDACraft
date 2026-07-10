#!/usr/bin/env python3
"""
可视化示例：1D-like PN 结（使用真 1D 网格保证收敛，再扩展为 2D 切片展示）
生成 3D 器件结构图 + 2D 仿真切片 + 1D 切割线图
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
# 1. 定义一个 1D PN 结（真 1D 网格：nx=41, ny=1, nz=1）
# ------------------------------------------------------------------
nx, ny, nz = 41, 1, 1
dx = dy = dz = 1e-9  # 1 nm spacing

sim = DeviceSimulator(nx, ny, nz, dx, dy, dz)
N = nx * ny * nz

# Doping: p-side (Na=1e18 cm^-3) on left, n-side (Nd=1e16 cm^-3) on right
# 注意：set_doping 接收的是 m^-3，需要乘以 1e6
doping = np.zeros(N)
for i in range(N):
    ix = i % nx
    if ix < nx // 2:
        doping[i] = -1e18 * 1e6   # p-side: -1e24 m^-3
    else:
        doping[i] = 1e16 * 1e6    # n-side: 1e22 m^-3
sim.set_doping(doping)

VT = 0.02585
ni = 1e16

# 平衡态电势
phi_n = VT * np.log(1e22 / ni)      # n-side 平衡态 ~ 0.357 V
phi_p = -VT * np.log(1e24 / ni)     # p-side 平衡态 ~ -0.476 V

# 只把最左/最右节点设为 Dirichlet 边界
left_nodes = [i for i in range(N) if (i % nx) == 0]
right_nodes = [i for i in range(N) if (i % nx) == nx - 1]

phi_bc = {}
n_bc = {}
p_bc = {}
for idx in left_nodes:
    phi_bc[idx] = phi_p
    n_bc[idx] = ni * ni / (1e24)   # ~1e8 m^-3
    p_bc[idx] = 1e24               # Na m^-3
for idx in right_nodes:
    phi_bc[idx] = phi_n
    n_bc[idx] = 1e22               # Nd m^-3
    p_bc[idx] = ni * ni / (1e22)   # ~1e10 m^-3

sim.set_dirichlet_potential(phi_bc)
sim.set_electron_bc(n_bc)
sim.set_hole_bc(p_bc)

sim.set_tolerance(1e-8)

# ------------------------------------------------------------------
# 2. 运行仿真
# ------------------------------------------------------------------
res = sim.solve()
print(f"Converged: {res['converged']}, Iterations: {res['iterations']}")

phi = res['phi'].reshape(nx, ny, nz)
n_arr = res['n'].reshape(nx, ny, nz)
p_arr = res['p'].reshape(nx, ny, nz)

# ------------------------------------------------------------------
# 3. 3D 器件结构图（matplotlib 线框）
# ------------------------------------------------------------------
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

L = (nx - 1) * dx
W = 4e-9   # 人为设置一个可视宽度
H = 4e-9   # 人为设置一个可视高度
x_j = (nx // 2 - 0.5) * dx

# p-side box
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
    faces_p, facecolors='steelblue', alpha=0.3, edgecolors='k', linewidths=0.5
))
ax.text(x_j/2, W/2, H/2, 'p-side\nNa=1e18', fontsize=9, ha='center')

# n-side box
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
    faces_n, facecolors='coral', alpha=0.3, edgecolors='k', linewidths=0.5
))
ax.text((x_j+L)/2, W/2, H/2, 'n-side\nNd=1e16', fontsize=9, ha='center')

# Contacts
ax.plot([0, 0], [0, W], [0, 0], 'r-', lw=3, label='p-contact')
ax.plot([L, L], [0, W], [0, 0], 'g-', lw=3, label='n-contact')

ax.set_xlabel('x [m]')
ax.set_ylabel('y [m]')
ax.set_zlabel('z [m]')
ax.set_title('PN Junction Device Structure')
ax.legend()
plt.tight_layout()
plt.savefig('pn3d_structure.png', dpi=150)
print('Saved: pn3d_structure.png')
plt.close()

# ------------------------------------------------------------------
# 4. 2D 仿真结果切片（将 1D 结果复制为伪 2D 切片，便于可视化）
# ------------------------------------------------------------------
ny_vis = 20
phi_2d = np.tile(phi[:, 0, 0], (ny_vis, 1))
n_2d = np.tile(n_arr[:, 0, 0], (ny_vis, 1))
p_2d = np.tile(p_arr[:, 0, 0], (ny_vis, 1))
dop_2d = np.tile(doping.reshape(nx, ny, nz)[:, 0, 0], (ny_vis, 1))

xx = np.linspace(0, L, nx)
yy_vis = np.linspace(0, W, ny_vis)
XX, YY = np.meshgrid(xx, yy_vis)

fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Potential
im0 = axes[0, 0].pcolormesh(XX, YY, phi_2d, cmap='viridis', shading='auto')
axes[0, 0].set_title('Electric Potential [V]')
axes[0, 0].set_xlabel('x [m]')
axes[0, 0].set_ylabel('y [m]')
fig.colorbar(im0, ax=axes[0, 0])

# log10(n)
log_n = np.log10(np.maximum(n_2d, 1e-10))
im1 = axes[0, 1].pcolormesh(XX, YY, log_n, cmap='plasma', shading='auto')
axes[0, 1].set_title(r'$\log_{10}(n)$ [m$^{-3}$]')
axes[0, 1].set_xlabel('x [m]')
axes[0, 1].set_ylabel('y [m]')
fig.colorbar(im1, ax=axes[0, 1])

# log10(p)
log_p = np.log10(np.maximum(p_2d, 1e-10))
im2 = axes[1, 0].pcolormesh(XX, YY, log_p, cmap='plasma', shading='auto')
axes[1, 0].set_title(r'$\log_{10}(p)$ [m$^{-3}$]')
axes[1, 0].set_xlabel('x [m]')
axes[1, 0].set_ylabel('y [m]')
fig.colorbar(im2, ax=axes[1, 0])

# Net charge
net = n_2d - p_2d + dop_2d
im3 = axes[1, 1].pcolormesh(XX, YY, net, cmap='RdBu_r', shading='auto')
axes[1, 1].set_title('Net Charge ($n - p + N_d - N_a$) [m$^{-3}$]')
axes[1, 1].set_xlabel('x [m]')
axes[1, 1].set_ylabel('y [m]')
fig.colorbar(im3, ax=axes[1, 1])

plt.suptitle('PN Junction Simulation Results (z-slice)', fontsize=14)
plt.tight_layout()
plt.savefig('pn3d_slices.png', dpi=150)
print('Saved: pn3d_slices.png')
plt.close()

# ------------------------------------------------------------------
# 5. 1D 切割线图（沿 x 轴中心线）
# ------------------------------------------------------------------
fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)

x_axis = xx
phi_1d = phi[:, 0, 0]
n_1d = n_arr[:, 0, 0]
p_1d = p_arr[:, 0, 0]
dop_1d = doping.reshape(nx, ny, nz)[:, 0, 0]

axes[0].plot(x_axis, phi_1d, 'b-o', markersize=4)
axes[0].axvline(x_j, color='k', linestyle='--', alpha=0.5, label='junction')
axes[0].set_ylabel('Potential [V]')
axes[0].set_title('1D Cutline across PN Junction')
axes[0].legend()
axes[0].grid(True)

axes[1].semilogy(x_axis, n_1d, 'r-o', markersize=4, label='n')
axes[1].semilogy(x_axis, p_1d, 'g-s', markersize=4, label='p')
axes[1].semilogy(x_axis, np.abs(dop_1d), 'k--', alpha=0.5, label='|Nd-Na|')
axes[1].set_ylabel('Density [m$^{-3}$]')
axes[1].legend()
axes[1].grid(True)

axes[2].plot(x_axis, n_1d - p_1d + dop_1d, 'm-o', markersize=4)
axes[2].axhline(0, color='k', linestyle='--', alpha=0.3)
axes[2].set_ylabel(r'$n - p + N_d - N_a$ [m$^{-3}$]')
axes[2].set_xlabel('x [m]')
axes[2].grid(True)

plt.tight_layout()
plt.savefig('pn3d_1d_cutline.png', dpi=150)
print('Saved: pn3d_1d_cutline.png')
plt.close()

print('\nAll visualization files generated successfully!')
