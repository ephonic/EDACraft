"""
Example: Planar MOSFET simulation with quantum correction.
"""

import numpy as np
import tcad
from tcad.viz.plotter import plot_device_geometry, plot_mesh_slice, plot_1d_cutline

# 1. Build device geometry
mosfet = tcad.Device.mosfet(
    Lg=50e-9,      # Gate length [m]
    tox=1.5e-9,    # Oxide thickness [m]
    tsi=20e-9,     # Silicon thickness [m]
    W=100e-9,      # Width [m]
    Lsd=50e-9,     # Source/Drain length [m]
    Vg=1.0,        # Gate voltage [V]
    Vd=0.5,        # Drain voltage [V]
    Vs=0.0,        # Source voltage [V]
)

# Visualize geometry
plot_device_geometry(mosfet)

# 2. Generate structured mesh
mesh = tcad.generate_mesh(mosfet, method="structured", resolution=(2e-9, 5e-9, 1e-9))
print(f"Mesh size: {mesh.nx} x {mesh.ny} x {mesh.nz} = {mesh.npts()} nodes")

# Quick look at doping slice
plot_mesh_slice(mesh, field="doping", axis="z", coord=10e-9)

# 3. Run simulation
sim, results = tcad.simulate_device(
    mosfet,
    resolution=(2e-9, 5e-9, 1e-9),
    temperature=300.0,
    quantum=True,
    max_iter=20,
    tol=1e-12,
)

print(f"Converged: {results['converged']}, Iterations: {results['iterations']}")

# 4. Attach results to mesh and visualize
fields = sim.to_mesh_fields()
for name, data in fields.items():
    mesh.add_field(name, data.ravel())

# Potential slice through the channel
plot_mesh_slice(mesh, field="phi", axis="y", coord=50e-9)

# Electron concentration (log scale)
mesh.add_field("log_n", np.log10(np.maximum(fields["n"], 1e-10).ravel()))
plot_mesh_slice(mesh, field="log_n", axis="y", coord=50e-9)

# 1D cutline from source to drain at surface
plot_1d_cutline(
    mesh, "phi",
    start=(0, 50e-9, 20e-9),
    end=(mosfet.bbox()[0][1], 50e-9, 20e-9),
)

# Save to VTK for ParaView
sim.save("mosfet_result.vtu")
print("Saved to mosfet_result.vtu")
