"""
Compare tcad 1D PN junction equilibrium solution against devsim reference.
Uses parameters known to converge robustly in both simulators.
"""

import numpy as np
import sys, os

# ------------------------------------------------------------------
# Physical parameters (matched to tcad defaults)
# ------------------------------------------------------------------
Na = 1e24       # p-side acceptors (m^-3)
Nd = 1e22       # n-side donors    (m^-3)
ni = 1e16       # intrinsic        (m^-3)
VT = 0.02585    # thermal voltage (V)

L = 40e-9       # device length, m
xj = 20e-9      # junction position, m

mu_n_si = 0.14   # m^2/(V*s)
mu_p_si = 0.045  # m^2/(V*s)
eps_tcad = 8.854187817e-12 * 11.7   # F/m

nx = 41
dx = L / (nx - 1)

# ------------------------------------------------------------------
# 1. Run devsim reference (cm units)
# ------------------------------------------------------------------
print("=" * 60)
print("Running devsim reference...")
print("=" * 60)

import devsim
from devsim.python_packages.simple_physics import (
    SetSiliconParameters,
    CreateSiliconPotentialOnly,
    CreateSiliconPotentialOnlyContact,
    CreateSiliconDriftDiffusion,
    CreateSiliconDriftDiffusionAtContact,
    GetContactBiasName,
)
from devsim.python_packages.model_create import CreateSolution

device = "MyDevice"
region = "MyRegion"

devsim.create_1d_mesh(mesh="dio")
L_cm = L * 1e2
xj_cm = xj * 1e2
dx_cm = dx * 1e2
for i in range(nx):
    devsim.add_1d_mesh_line(mesh="dio", pos=i*dx_cm, ps=dx_cm, tag=f"n{i}")
devsim.add_1d_contact(mesh="dio", name="top", tag="n0", material="metal")
devsim.add_1d_contact(mesh="dio", name="bot", tag=f"n{nx-1}", material="metal")
devsim.add_1d_region(mesh="dio", material="Si", region=region, tag1="n0", tag2=f"n{nx-1}")
devsim.finalize_mesh(mesh="dio")
devsim.create_device(mesh="dio", device=device)

SetSiliconParameters(device, region, 300)

# Override to match tcad
devsim.set_parameter(device=device, region=region, name="Permittivity", value=eps_tcad * 1e-2)
devsim.set_parameter(device=device, region=region, name="ElectronCharge", value=1.602176634e-19)
devsim.set_parameter(device=device, region=region, name="n_i", value=ni * 1e-6)
devsim.set_parameter(device=device, region=region, name="V_t", value=VT)
devsim.set_parameter(device=device, region=region, name="mu_n", value=mu_n_si * 1e4)
devsim.set_parameter(device=device, region=region, name="mu_p", value=mu_p_si * 1e4)

Na_cm = Na * 1e-6
Nd_cm = Nd * 1e-6
devsim.node_model(device=device, region=region, name="Acceptors", equation=f"{Na_cm}*step({xj_cm}-x)")
devsim.node_model(device=device, region=region, name="Donors",    equation=f"{Nd_cm}*step(x-{xj_cm})")
devsim.node_model(device=device, region=region, name="NetDoping", equation="Donors-Acceptors")

CreateSolution(device, region, "Potential")
CreateSiliconPotentialOnly(device, region)
for contact in devsim.get_contact_list(device=device):
    devsim.set_parameter(device=device, name=GetContactBiasName(contact), value=0.0)
    CreateSiliconPotentialOnlyContact(device, region, contact)

devsim.solve(type="dc", absolute_error=1.0, relative_error=1e-10, maximum_iterations=30)

CreateSolution(device, region, "Electrons")
CreateSolution(device, region, "Holes")
devsim.set_node_values(device=device, region=region, name="Electrons", init_from="IntrinsicElectrons")
devsim.set_node_values(device=device, region=region, name="Holes",     init_from="IntrinsicHoles")
CreateSiliconDriftDiffusion(device, region)
for contact in devsim.get_contact_list(device=device):
    CreateSiliconDriftDiffusionAtContact(device, region, contact)

devsim.solve(type="dc", absolute_error=1e10, relative_error=1e-10, maximum_iterations=100)

# Extract
x_dev_cm = np.array(devsim.get_node_model_values(device=device, region=region, name="x"))
phi_dev = np.array(devsim.get_node_model_values(device=device, region=region, name="Potential"))
n_dev_cm = np.array(devsim.get_node_model_values(device=device, region=region, name="Electrons"))
p_dev_cm = np.array(devsim.get_node_model_values(device=device, region=region, name="Holes"))
Nd_dev_cm = np.array(devsim.get_node_model_values(device=device, region=region, name="NetDoping"))

x_dev = x_dev_cm * 1e-2
n_dev = n_dev_cm * 1e6
p_dev = p_dev_cm * 1e6
Nd_dev = Nd_dev_cm * 1e6

devsim.edge_average_model(device=device, region=region, node_model="x", edge_model="xmid")
xmid_dev_cm = np.array(devsim.get_edge_model_values(device=device, region=region, name="xmid"))
E_dev_cm = np.array(devsim.get_edge_model_values(device=device, region=region, name="ElectricField"))
xmid_dev = xmid_dev_cm * 1e-2
E_dev = E_dev_cm * 1e2

print(f"devsim: phi range [{phi_dev.min():.3f}, {phi_dev.max():.3f}] V")
print(f"devsim: n range [{n_dev.min():.3e}, {n_dev.max():.3e}] m^-3")
print(f"devsim: p range [{p_dev.min():.3e}, {p_dev.max():.3e}] m^-3")

# ------------------------------------------------------------------
# 2. Run tcad
# ------------------------------------------------------------------
print("\n" + "=" * 60)
print("Running tcad...")
print("=" * 60)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tcad.core import PyDeviceSimulator as DeviceSimulator

sim = DeviceSimulator(nx, 1, 1, dx, dx, dx)
N = nx
doping = np.zeros(N)
doping[:N//2] = Nd
doping[N//2:] = -Na
sim.set_doping(doping)
sim.set_permittivity(np.ones(N) * eps_tcad)
sim.set_mobility(np.ones(N) * mu_n_si, np.ones(N) * mu_p_si)

phi_n = VT * np.log(Nd / ni)
phi_p = -VT * np.log(Na / ni)
phi_bc = {0: phi_p, nx-1: phi_n}
n_bc = {0: ni*ni/Na, nx-1: Nd}
p_bc = {0: Na, nx-1: ni*ni/Nd}

sim.set_dirichlet_potential(phi_bc)
sim.set_electron_bc(n_bc)
sim.set_hole_bc(p_bc)
sim.set_tolerance(1e-8)
sim.set_gummel_max_iter(100)

res = sim.solve()
print(f"tcad: converged={res['converged']}, iters={res['iterations']}")

x_tcad = np.arange(nx) * dx
phi_tcad = res['phi']
n_tcad = res['n']
p_tcad = res['p']
Ex_tcad = res['Ex']

print(f"tcad: phi range [{phi_tcad.min():.3f}, {phi_tcad.max():.3f}] V")
print(f"tcad: n range [{n_tcad.min():.3e}, {n_tcad.max():.3e}] m^-3")
print(f"tcad: p range [{p_tcad.min():.3e}, {p_tcad.max():.3e}] m^-3")

# ------------------------------------------------------------------
# 3. Compare
# ------------------------------------------------------------------
print("\n" + "=" * 60)
print("Comparison")
print("=" * 60)

from scipy.interpolate import interp1d

phi_tcad_i = interp1d(x_tcad, phi_tcad, kind='cubic', fill_value='extrapolate')(x_dev)
n_tcad_i = interp1d(x_tcad, n_tcad, kind='cubic', fill_value='extrapolate')(x_dev)
p_tcad_i = interp1d(x_tcad, p_tcad, kind='cubic', fill_value='extrapolate')(x_dev)

err_phi = np.abs(phi_tcad_i - phi_dev)
err_n = np.abs(n_tcad_i - n_dev)
err_p = np.abs(p_tcad_i - p_dev)

phi_scale = np.abs(phi_dev).max() + 1e-10
n_scale = n_dev.max() + 1e10
p_scale = p_dev.max() + 1e10

print(f"Phi max abs error: {err_phi.max():.3e} V")
print(f"Phi mean abs error: {err_phi.mean():.3e} V")
print(f"Phi rel error: {100*err_phi.max()/phi_scale:.4f}%")

mask_n = n_dev > 1e12
mask_p = p_dev > 1e12
print(f"n  max rel error: {100*(err_n[mask_n]/n_dev[mask_n]).max():.4f}%")
print(f"p  max rel error: {100*(err_p[mask_p]/p_dev[mask_p]).max():.4f}%")

Ex_tcad_edge = 0.5 * (Ex_tcad[:-1] + Ex_tcad[1:])
x_edge_tcad = 0.5 * (x_tcad[:-1] + x_tcad[1:])
Ex_tcad_i = interp1d(x_edge_tcad, Ex_tcad_edge, kind='cubic', fill_value='extrapolate')(xmid_dev)
err_E = np.abs(Ex_tcad_i - E_dev)
E_scale = np.abs(E_dev).max() + 1e-10
print(f"E  max abs error: {err_E.max():.3e} V/m")
print(f"E  max rel error: {100*err_E.max()/E_scale:.4f}%")

jx = int(xj / dx)
print(f"\nJunction region (nodes {jx-2}:{jx+2}):")
print("  node | x(nm) | phi_dev | phi_tcad | dphi")
for i in range(max(0,jx-2), min(nx,jx+3)):
    print(f"  {i:4d} | {x_dev[i]*1e9:5.2f} | {phi_dev[i]:9.4f} | {phi_tcad[i]:10.4f} | {abs(phi_dev[i]-phi_tcad[i]):.4f}")

# ------------------------------------------------------------------
# 4. Plot
# ------------------------------------------------------------------
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 2, figsize=(12, 9))

ax = axes[0, 0]
ax.plot(x_dev * 1e9, phi_dev, 'o-', label='devsim', markersize=3)
ax.plot(x_tcad * 1e9, phi_tcad, 's--', label='tcad', markersize=3)
ax.set_xlabel('x (nm)')
ax.set_ylabel('Potential (V)')
ax.set_title('Potential')
ax.legend()
ax.grid(True)

ax = axes[0, 1]
ax.semilogy(x_dev * 1e9, n_dev, 'o-', label='devsim n', markersize=3)
ax.semilogy(x_dev * 1e9, p_dev, 'o-', label='devsim p', markersize=3)
ax.semilogy(x_tcad * 1e9, n_tcad, 's--', label='tcad n', markersize=3)
ax.semilogy(x_tcad * 1e9, p_tcad, 's--', label='tcad p', markersize=3)
ax.set_xlabel('x (nm)')
ax.set_ylabel('Carrier density (m^-3)')
ax.set_title('Electron & Hole densities')
ax.legend()
ax.grid(True)

ax = axes[1, 0]
ax.plot(x_dev * 1e9, Nd_dev, 'o-', label='devsim NetDoping', markersize=3)
ax.plot(x_tcad * 1e9, doping, 's--', label='tcad Nd-Na', markersize=3)
ax.set_xlabel('x (nm)')
ax.set_ylabel('Doping (m^-3)')
ax.set_title('Net Doping')
ax.legend()
ax.grid(True)

ax = axes[1, 1]
ax.plot(xmid_dev * 1e9, E_dev, 'o-', label='devsim', markersize=3)
ax.plot(x_edge_tcad * 1e9, Ex_tcad_edge, 's--', label='tcad', markersize=3)
ax.set_xlabel('x (nm)')
ax.set_ylabel('E-field (V/m)')
ax.set_title('Electric Field')
ax.legend()
ax.grid(True)

plt.tight_layout()
plt.savefig('compare_devsim_1d_pn.png', dpi=150)
print("\nSaved plot to compare_devsim_1d_pn.png")
