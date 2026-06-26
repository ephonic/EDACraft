#!/usr/bin/env python3
"""
2D MOSFET simulation with tcad.

NOTE ON LIMITATIONS:
- This demo uses conservative doping (Nd=1e22, Na=1e21) so Gummel converges.
- The gate is modeled as a Dirichlet phi boundary with zero-flux Neumann
  for n/p (metal/insulator interface).  This is physically correct but
  makes the Poisson-continuity coupling strong.
- Gummel iteration becomes unstable for Vgs > ~0.2 V (strong inversion).
  A Newton-Raphson solver or much stronger damping would be needed for
  deep subthreshold / strong-inversion regimes.
- The thin device (30 nm) means source/drain electrons diffuse across the
  entire surface even at equilibrium, so the "off" state is not perfectly
  p-type in the channel.  A thicker body and longer channel would give
  more textbook-like profiles.
"""
import numpy as np
import matplotlib.pyplot as plt
from tcad.core import PyDeviceSimulator as DeviceSimulator

# Physical constants
VT = 0.02585
ni = 1e16
EPS0 = 8.854e-12

# Device geometry
L = 100e-9       # Channel length [m]
t_si = 30e-9     # Silicon thickness [m]
nx = 31
ny = 7
dx = L / (nx - 1)
dy = t_si / (ny - 1)

# Region definitions (grid indices)
idx_source_x = int(15e-9 / dx)
idx_source_y = int(12e-9 / dy)
idx_drain_x_start = nx - 1 - int(15e-9 / dx)

print(f"Grid: {nx}x{ny} = {nx*ny} nodes, dx={dx*1e9:.1f}nm, dy={dy*1e9:.1f}nm")

# Doping: Source/Drain n-type, Body p-type
Nd_SD = 1e22
Na_B = 1e21
Nd_minus_Na = np.ones(nx * ny) * (-Na_B)
for j in range(idx_source_y):
    for i in range(idx_source_x + 1):
        Nd_minus_Na[j * nx + i] = Nd_SD
    for i in range(idx_drain_x_start, nx):
        Nd_minus_Na[j * nx + i] = Nd_SD

# Material properties
eps = np.ones(nx * ny) * EPS0 * 11.7
mu_n = np.ones(nx * ny) * 0.14
mu_p = np.ones(nx * ny) * 0.045

# Build simulator
sim = DeviceSimulator(nx, ny, 1, dx, dy, dx)
sim.set_doping(Nd_minus_Na)
sim.set_permittivity(eps)
sim.set_mobility(mu_n, mu_p)

# Contact node indices
source_nodes = [j * nx + 0 for j in range(ny)]
drain_nodes = [j * nx + (nx - 1) for j in range(ny)]
body_nodes = [(ny - 1) * nx + i for i in range(nx)]
gate_start = int(15e-9 / dx)
gate_end = nx - 1 - int(15e-9 / dx)
gate_nodes = [0 * nx + i for i in range(gate_start, gate_end + 1)]

# Helper to set BCs
def set_bcs(sim, Vgs, Vds):
    phi_bc = {}
    n_bc = {}
    p_bc = {}
    
    for idx in source_nodes:
        phi_bc[idx] = 0.0
        n_bc[idx] = Nd_SD
        p_bc[idx] = ni**2 / Nd_SD
    for idx in drain_nodes:
        phi_bc[idx] = Vds
        n_bc[idx] = Nd_SD
        p_bc[idx] = ni**2 / Nd_SD
    for idx in body_nodes:
        phi_bc[idx] = 0.0
        n_bc[idx] = ni**2 / Na_B
        p_bc[idx] = Na_B
    for idx in gate_nodes:
        phi_bc[idx] = Vgs
        # Gate is a metal/insulator interface: only phi is fixed.
        # n/p are NOT Dirichlet -> continuity solver sees zero-flux Neumann.
    
    sim.set_dirichlet_potential(phi_bc)
    sim.set_electron_bc(n_bc)
    sim.set_hole_bc(p_bc)

# Run simulations
sim.set_tolerance(1e-6)
sim.set_gummel_max_iter(200)

configs = [
    ("Equilibrium", 0.0, 0.0),
    ("Weak gate (Vgs=0.1V)", 0.1, 0.0),
    ("Weak gate (Vgs=0.2V)", 0.2, 0.0),
]
results = {}

for name, Vgs, Vds in configs:
    set_bcs(sim, Vgs, Vds)
    res = sim.solve()
    print(f"{name}: converged={res['converged']}, iters={res['iterations']}")
    if res['converged']:
        results[name] = res

# Plotting
if results:
    x = np.linspace(0, L, nx) * 1e9
    y = np.linspace(0, t_si, ny) * 1e9
    
    fig, axes = plt.subplots(len(results), 3, figsize=(14, 4*len(results)))
    if len(results) == 1:
        axes = axes.reshape(1, -1)
    
    for row, (name, res) in enumerate(results.items()):
        phi = res['phi'].reshape(ny, nx)
        n = res['n'].reshape(ny, nx)
        p = res['p'].reshape(ny, nx)
        
        ax = axes[row, 0]
        im = ax.pcolormesh(x, y, phi, shading='auto', cmap='RdBu_r')
        ax.set_title(f"{name}: Potential [V]")
        ax.set_xlabel('x [nm]')
        ax.set_ylabel('y [nm]')
        plt.colorbar(im, ax=ax)
        
        ax = axes[row, 1]
        im = ax.pcolormesh(x, y, np.log10(n), shading='auto', cmap='viridis', vmin=10, vmax=22)
        ax.set_title(f"{name}: log10(n)")
        ax.set_xlabel('x [nm]')
        ax.set_ylabel('y [nm]')
        plt.colorbar(im, ax=ax)
        
        ax = axes[row, 2]
        im = ax.pcolormesh(x, y, np.log10(p), shading='auto', cmap='plasma', vmin=10, vmax=22)
        ax.set_title(f"{name}: log10(p)")
        ax.set_xlabel('x [nm]')
        ax.set_ylabel('y [nm]')
        plt.colorbar(im, ax=ax)
    
    plt.tight_layout()
    plt.savefig('mosfet_2d_results.png', dpi=150)
    print("\nSaved plot to mosfet_2d_results.png")
    
    # Surface profiles
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    ax = axes[0]
    for name, res in results.items():
        ax.semilogy(x, res['n'].reshape(ny, nx)[0, :], label=name)
    ax.axhline(Na_B, color='k', ls='--', alpha=0.3, label='Na')
    ax.set_xlabel('x [nm]')
    ax.set_ylabel('n [m^-3]')
    ax.set_title('Surface Electron Concentration')
    ax.legend()
    
    ax = axes[1]
    for name, res in results.items():
        ax.plot(x, res['phi'].reshape(ny, nx)[0, :], label=name)
    ax.set_xlabel('x [nm]')
    ax.set_ylabel('phi [V]')
    ax.set_title('Surface Potential')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig('mosfet_2d_surface.png', dpi=150)
    print("Saved surface profiles to mosfet_2d_surface.png")
    
    # Print summary
    print("\n--- Summary ---")
    phi_F = VT * np.log(Na_B / ni)
    print(f"phi_F = {phi_F:.3f} V, 2*phi_F = {2*phi_F:.3f} V")
    for name, res in results.items():
        n_mid = res['n'].reshape(ny, nx)[0, nx//2]
        phi_mid = res['phi'].reshape(ny, nx)[0, nx//2]
        print(f"{name}: phi_mid={phi_mid:.3f}V, n_mid={n_mid:.3e} m^-3")
