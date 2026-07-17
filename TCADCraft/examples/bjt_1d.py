#!/usr/bin/env python3
"""1D NPN BJT simulation with tcad."""
import numpy as np
import matplotlib.pyplot as plt
from tcad.core import PyDeviceSimulator as DeviceSimulator

# Physical constants
VT = 0.02585      # Thermal voltage [V]
ni = 1e16         # Intrinsic concentration [m^-3]
QE = 1.602e-19    # Electron charge [C]
EPS0 = 8.854e-12

# Device geometry (1D)
L_total = 150e-9   # Total length [m]
nx = 151           # Grid points
dx = L_total / (nx - 1)

# Region boundaries
L_emitter = 50e-9
L_base = 20e-9
L_collector = L_total - L_emitter - L_base

idx_e = int(L_emitter / dx)
idx_b = int((L_emitter + L_base) / dx)

x = np.linspace(0, L_total, nx) * 1e9  # [nm]

# --- Doping profile ---
# Case 1: Moderate doping (converges with Gummel)
Nd_E = 1e22   # Emitter n-type [m^-3]
Na_B = 1e21   # Base p-type [m^-3]
Nd_C = 1e20   # Collector n-type [m^-3]

# Case 2: High doping (may cause NaN - uncomment to test)
# Nd_E = 1e25
# Na_B = 1e24
# Nd_C = 1e22

Nd_minus_Na = np.zeros(nx)
Nd_minus_Na[:idx_e] = Nd_E
Nd_minus_Na[idx_e:idx_b] = -Na_B
Nd_minus_Na[idx_b:] = Nd_C

eps = EPS0 * 11.7
mu_n = 0.14   # [m^2/V/s]
mu_p = 0.045  # [m^2/V/s]

# Build simulator
sim = DeviceSimulator(nx, 1, 1, dx, dx, dx)
sim.set_doping(Nd_minus_Na)
sim.set_permittivity(np.ones(nx) * eps)
sim.set_mobility(np.ones(nx) * mu_n, np.ones(nx) * mu_p)

# Equilibrium contact potentials
phi_n_E = VT * np.log(Nd_E / ni)
phi_p_B = -VT * np.log(Na_B / ni)
phi_n_C = VT * np.log(Nd_C / ni)

print(f"Emitter:  Nd={Nd_E:.0e} m^-3, phi_eq={phi_n_E:.3f} V")
print(f"Base:     Na={Na_B:.0e} m^-3, phi_eq={phi_p_B:.3f} V")
print(f"Collector: Nd={Nd_C:.0e} m^-3, phi_eq={phi_n_C:.3f} V")

# Dirichlet BCs: both contacts grounded at equilibrium
# For n-type contacts, the equilibrium potential in bulk is phi_n
# We set contact phi = 0 (ground), but the initial guess uses local charge neutrality
phi_bc = {0: 0.0, nx - 1: 0.0}
n_bc = {0: Nd_E, nx - 1: Nd_C}
p_bc = {0: ni**2 / Nd_E, nx - 1: ni**2 / Nd_C}

sim.set_dirichlet_potential(phi_bc)
sim.set_electron_bc(n_bc)
sim.set_hole_bc(p_bc)
sim.set_tolerance(1e-6)
sim.set_gummel_max_iter(200)

# ===== Equilibrium solve =====
print("\n--- Equilibrium ---")
res_eq = sim.solve()
print(f"Converged: {res_eq['converged']}, Iterations: {res_eq['iterations']}")
print(f"phi range: [{res_eq['phi'].min():.4f}, {res_eq['phi'].max():.4f}] V")
print(f"n range:   [{res_eq['n'].min():.3e}, {res_eq['n'].max():.3e}] m^-3")
print(f"p range:   [{res_eq['p'].min():.3e}, {res_eq['p'].max():.3e}] m^-3")

# ===== Forward active bias =====
print("\n--- Forward Active ---")
V_BE = 0.7   # Base-Emitter forward bias
V_CB = 2.0   # Collector-Base reverse bias

# Apply bias: emitter grounded, base at V_BE, collector at V_BE + V_CB
phi_bc_fa = {0: 0.0, nx - 1: V_BE + V_CB}
sim.set_dirichlet_potential(phi_bc_fa)

# Carrier BCs at contacts (quasi-neutral approximation)
# Emitter contact (n-type, grounded)
n_bc_fa = {0: Nd_E, nx - 1: Nd_C}
p_bc_fa = {0: ni**2 / Nd_E, nx - 1: ni**2 / Nd_C}

sim.set_electron_bc(n_bc_fa)
sim.set_hole_bc(p_bc_fa)

res_fa = sim.solve()
print(f"Converged: {res_fa['converged']}, Iterations: {res_fa['iterations']}")
if res_fa['converged']:
    print(f"phi range: [{res_fa['phi'].min():.4f}, {res_fa['phi'].max():.4f}] V")
    print(f"n range:   [{res_fa['n'].min():.3e}, {res_fa['n'].max():.3e}] m^-3")
    print(f"p range:   [{res_fa['p'].min():.3e}, {res_fa['p'].max():.3e}] m^-3")

# ===== Plotting =====
fig, axes = plt.subplots(2, 2, figsize=(12, 9))

# Doping
ax = axes[0, 0]
ax.semilogy(x, np.abs(Nd_minus_Na), 'k-', label='|Nd-Na|')
ax.axvline(L_emitter * 1e9, color='r', ls='--', alpha=0.5)
ax.axvline((L_emitter + L_base) * 1e9, color='r', ls='--', alpha=0.5)
ax.set_xlabel('x [nm]')
ax.set_ylabel('Doping [m$^{-3}$]')
ax.set_title('Doping Profile')
ax.legend()

# Potential
ax = axes[0, 1]
ax.plot(x, res_eq['phi'], 'b-', label='Equilibrium')
if res_fa['converged']:
    ax.plot(x, res_fa['phi'], 'r-', label='Forward Active')
ax.axvline(L_emitter * 1e9, color='gray', ls='--', alpha=0.5)
ax.axvline((L_emitter + L_base) * 1e9, color='gray', ls='--', alpha=0.5)
ax.set_xlabel('x [nm]')
ax.set_ylabel('Potential [V]')
ax.set_title('Electrostatic Potential')
ax.legend()

# Electron concentration
ax = axes[1, 0]
ax.semilogy(x, res_eq['n'], 'b-', label='Equilibrium')
if res_fa['converged']:
    ax.semilogy(x, res_fa['n'], 'r-', label='Forward Active')
ax.axvline(L_emitter * 1e9, color='gray', ls='--', alpha=0.5)
ax.axvline((L_emitter + L_base) * 1e9, color='gray', ls='--', alpha=0.5)
ax.set_xlabel('x [nm]')
ax.set_ylabel('n [m$^{-3}$]')
ax.set_title('Electron Concentration')
ax.legend()

# Hole concentration
ax = axes[1, 1]
ax.semilogy(x, res_eq['p'], 'b-', label='Equilibrium')
if res_fa['converged']:
    ax.semilogy(x, res_fa['p'], 'r-', label='Forward Active')
ax.axvline(L_emitter * 1e9, color='gray', ls='--', alpha=0.5)
ax.axvline((L_emitter + L_base) * 1e9, color='gray', ls='--', alpha=0.5)
ax.set_xlabel('x [nm]')
ax.set_ylabel('p [m$^{-3}$]')
ax.set_title('Hole Concentration')
ax.legend()

plt.tight_layout()
plt.savefig('bjt_1d_results.png', dpi=150)
print("\nSaved plot to bjt_1d_results.png")

# Band diagram (approximate)
Ec = -res_eq['phi'] * QE   # Conduction band edge [J] (relative to Ef=0)
Ev = Ec - 1.12 * QE        # Valence band edge
Ev_fa = -res_fa['phi'] * QE - 1.12 * QE if res_fa['converged'] else None

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(x, Ec / QE, 'b-', label='$E_c$ (eq)')
ax.plot(x, Ev / QE, 'b--', label='$E_v$ (eq)')
if res_fa['converged']:
    ax.plot(x, -res_fa['phi'], 'r-', label='$E_c$ (FA)')
    ax.plot(x, Ev_fa / QE, 'r--', label='$E_v$ (FA)')
ax.axhline(0, color='k', ls='-', alpha=0.3, label='$E_F$')
ax.axvline(L_emitter * 1e9, color='gray', ls='--', alpha=0.5)
ax.axvline((L_emitter + L_base) * 1e9, color='gray', ls='--', alpha=0.5)
ax.set_xlabel('x [nm]')
ax.set_ylabel('Energy [eV]')
ax.set_title('Band Diagram')
ax.legend()
plt.tight_layout()
plt.savefig('bjt_1d_bands.png', dpi=150)
print("Saved band diagram to bjt_1d_bands.png")
