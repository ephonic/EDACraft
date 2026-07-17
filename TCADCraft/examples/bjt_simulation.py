"""
1D Vertical NPN BJT simulation.

Structure (bottom to top, y-direction):
  - Emitter:    y = 0-50 nm,   n+ type, Nd = 1e25
  - Base:       y = 50-70 nm,  p-type,  Na = 1e23
  - Collector:  y = 70-150 nm, n-type,  Nd = 1e21

Contacts:
  - Emitter:  y = 0
  - Base:     y = 60 nm (approximate side-contact in 1D)
  - Collector: y = 150 nm
"""

import numpy as np
import matplotlib.pyplot as plt
from tcad.core import PyDeviceSimulator as DeviceSimulator

# Physical constants
K_B = 1.3806503e-23
Q_E = 1.602176634e-19
EPS0 = 8.854187817e-12
VT = 0.02585
ni = 1e16

# 1D Geometry
L = 150e-9
nx = 151
dx = L / (nx - 1)

print(f"1D BJT grid: {nx} points, dx={dx*1e9:.1f}nm")

# Region boundaries (in nm)
y_emitter = 50e-9
y_base = 70e-9

idx_emitter = int(y_emitter / dx)
idx_base = int(y_base / dx)
idx_base_contact = int(60e-9 / dx)  # middle of base

# Doping
Nd_minus_Na = np.zeros(nx)
Nd_minus_Na[:idx_emitter] = 1e25
Nd_minus_Na[idx_emitter:idx_base] = -1e23
Nd_minus_Na[idx_base:] = 1e21

# Material properties
eps = EPS0 * 11.7
mu_n = 0.14
mu_p = 0.045

# Create simulator
sim = DeviceSimulator(nx, 1, 1, dx, dx, dx)
sim.set_doping(Nd_minus_Na)
sim.set_permittivity(np.ones(nx) * eps)
sim.set_mobility(np.ones(nx) * mu_n, np.ones(nx) * mu_p)

# Equilibrium potentials
phi_n_emitter = VT * np.log(1e25 / ni)
phi_p_base = -VT * np.log(1e23 / ni)
phi_n_collector = VT * np.log(1e21 / ni)

print(f"Equilibrium potentials: phi_E={phi_n_emitter:.3f}V, phi_B={phi_p_base:.3f}V, phi_C={phi_n_collector:.3f}V")

# --- Equilibrium ---
phi_bc_eq = {
    0: 0.0,
    nx - 1: 0.0,
    idx_base_contact: phi_p_base,
}
n_bc_eq = {
    0: 1e25,
    nx - 1: 1e21,
    idx_base_contact: ni * ni / 1e23,
}
p_bc_eq = {
    0: ni * ni / 1e25,
    nx - 1: ni * ni / 1e21,
    idx_base_contact: 1e23,
}

sim.set_dirichlet_potential(phi_bc_eq)
sim.set_electron_bc(n_bc_eq)
sim.set_hole_bc(p_bc_eq)
sim.set_tolerance(1e-6)
sim.set_gummel_max_iter(100)

print("Solving equilibrium...")
res_eq = sim.solve()
print(f"Equilibrium: converged={res_eq['converged']}, iterations={res_eq['iterations']}")

x_nm = np.arange(nx) * dx * 1e9

# --- Forward Active Bias ---
# V_BE = 0.7 V (forward bias emitter-base)
# V_CB = 2.0 V (reverse bias collector-base)
V_BE = 0.7
V_CB = 2.0
phi_E = 0.0
phi_B = phi_E + V_BE
phi_C = phi_B + V_CB

print(f"\nBias: V_BE={V_BE}V, V_CB={V_CB}V")
print(f"Contact potentials: E={phi_E:.2f}V, B={phi_B:.2f}V, C={phi_C:.2f}V")

phi_bc_bias = {
    0: phi_E,
    nx - 1: phi_C,
    idx_base_contact: phi_B,
}
# Carrier BCs: use equilibrium values shifted by exp(qV/kT)
n_bc_bias = {
    0: 1e25,
    nx - 1: 1e21,
    idx_base_contact: ni * ni / 1e23 * np.exp(phi_B / VT),
}
p_bc_bias = {
    0: ni * ni / 1e25,
    nx - 1: ni * ni / 1e21,
    idx_base_contact: 1e23 * np.exp(-phi_B / VT),
}

sim.set_dirichlet_potential(phi_bc_bias)
sim.set_electron_bc(n_bc_bias)
sim.set_hole_bc(p_bc_bias)

print("Solving forward active...")
res_bias = sim.solve()
print(f"Forward active: converged={res_bias['converged']}, iterations={res_bias['iterations']}")

# --- Plotting ---
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Row 0: Equilibrium
axes[0, 0].plot(x_nm, res_eq['phi'], 'b-', lw=2)
axes[0, 0].axvline(y_emitter*1e9, color='r', ls='--', alpha=0.5, label='E-B junction')
axes[0, 0].axvline(y_base*1e9, color='g', ls='--', alpha=0.5, label='B-C junction')
axes[0, 0].axvline(60, color='orange', ls=':', alpha=0.5, label='Base contact')
axes[0, 0].set_title('Equilibrium: Potential')
axes[0, 0].set_ylabel('phi (V)')
axes[0, 0].legend(fontsize=8)
axes[0, 0].grid(True, alpha=0.3)

axes[0, 1].semilogy(x_nm, res_eq['n'], 'b-', lw=2, label='n')
axes[0, 1].semilogy(x_nm, res_eq['p'], 'r-', lw=2, label='p')
axes[0, 1].axvline(y_emitter*1e9, color='r', ls='--', alpha=0.5)
axes[0, 1].axvline(y_base*1e9, color='g', ls='--', alpha=0.5)
axes[0, 1].set_title('Equilibrium: Carriers')
axes[0, 1].set_ylabel('concentration (m^-3)')
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)

# Row 1: Biased
axes[1, 0].plot(x_nm, res_eq['phi'], 'b--', lw=1.5, alpha=0.7, label='equilibrium')
axes[1, 0].plot(x_nm, res_bias['phi'], 'r-', lw=2, label='biased')
axes[1, 0].axvline(y_emitter*1e9, color='r', ls='--', alpha=0.5)
axes[1, 0].axvline(y_base*1e9, color='g', ls='--', alpha=0.5)
axes[1, 0].axhline(phi_B, color='orange', ls=':', alpha=0.5)
axes[1, 0].axhline(phi_C, color='purple', ls=':', alpha=0.5)
axes[1, 0].set_title(f'Potential (V_BE={V_BE}V, V_CB={V_CB}V)')
axes[1, 0].set_xlabel('y (nm)')
axes[1, 0].set_ylabel('phi (V)')
axes[1, 0].legend()
axes[1, 0].grid(True, alpha=0.3)

axes[1, 1].semilogy(x_nm, res_bias['n'], 'b-', lw=2, label='n')
axes[1, 1].semilogy(x_nm, res_bias['p'], 'r-', lw=2, label='p')
axes[1, 1].axvline(y_emitter*1e9, color='r', ls='--', alpha=0.5)
axes[1, 1].axvline(y_base*1e9, color='g', ls='--', alpha=0.5)
axes[1, 1].set_title('Biased: Carriers')
axes[1, 1].set_xlabel('y (nm)')
axes[1, 1].set_ylabel('concentration (m^-3)')
axes[1, 1].legend()
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('bjt_1d_results.png', dpi=150)
plt.close()
print("Saved bjt_1d_results.png")

# Summary statistics
print(f"\n--- Equilibrium ---")
print(f"phi range: [{res_eq['phi'].min():.3f}, {res_eq['phi'].max():.3f}] V")
print(f"n max: {res_eq['n'].max():.3e}")
print(f"p max: {res_eq['p'].max():.3e}")

print(f"\n--- Forward Active (V_BE={V_BE}V, V_CB={V_CB}V) ---")
print(f"phi range: [{res_bias['phi'].min():.3f}, {res_bias['phi'].max():.3f}] V")
print(f"n max: {res_bias['n'].max():.3e}")
print(f"p max: {res_bias['p'].max():.3e}")

# Estimate current gain
# Electron current at emitter and collector
# Using SG formula at the junctions

from scipy.interpolate import interp1d

def bernoulli(x):
    x = np.asarray(x)
    result = np.empty_like(x, dtype=float)
    small = np.abs(x) < 1e-12
    result[small] = 1.0
    big_pos = x > 100
    result[big_pos] = 0.0
    big_neg = x < -100
    result[big_neg] = -x[big_neg]
    rest = ~(small | big_pos | big_neg)
    result[rest] = x[rest] / np.expm1(x[rest])
    return result

phi_b = res_bias['phi']
n_b = res_bias['n']
p_b = res_bias['p']

# Electron current at E-B junction (idx_emitter -> idx_emitter+1)
dphi_eb = phi_b[idx_emitter+1] - phi_b[idx_emitter]
Bp_eb = bernoulli(dphi_eb / VT)
Bm_eb = bernoulli(-dphi_eb / VT)
Dn = mu_n * VT / dx
Jn_eb = Q_E * Dn * (n_b[idx_emitter] * Bm_eb - n_b[idx_emitter+1] * Bp_eb)

# Electron current at B-C junction (idx_base-1 -> idx_base)
dphi_bc = phi_b[idx_base] - phi_b[idx_base-1]
Bp_bc = bernoulli(dphi_bc / VT)
Bm_bc = bernoulli(-dphi_bc / VT)
Jn_bc = Q_E * Dn * (n_b[idx_base-1] * Bm_bc - n_b[idx_base] * Bp_bc)

print(f"\n--- Current estimates ---")
print(f"Electron current at E-B junction: {Jn_eb:.3e} A/m^2")
print(f"Electron current at B-C junction: {Jn_bc:.3e} A/m^2")
print(f"Electron transport factor: {Jn_bc/Jn_eb:.4f}" if Jn_eb != 0 else "")

print("\nBJT simulation complete!")
