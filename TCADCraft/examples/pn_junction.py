"""
Example: 1D-like PN junction in 3D.
"""

import tcad
from tcad.viz.plotter import plot_mesh_slice, plot_1d_cutline

pn = tcad.Device.pnjunction(
    L=2e-6, W=1e-6, H=1e-6,
    x_junction=1e-6,
    Na=1e16, Nd=1e16,
)

sim, results = tcad.simulate_device(pn, resolution=(20e-9, 100e-9, 100e-9),
                                     quantum=False, max_iter=30)

print(f"PN junction converged: {results['converged']}")

fields = sim.to_mesh_fields()
for name, data in fields.items():
    sim.mesh.add_field(name, data.ravel())

# Potential across junction
plot_1d_cutline(sim.mesh, "phi", start=(0, 0.5e-6, 0.5e-6), end=(2e-6, 0.5e-6, 0.5e-6))

sim.save("pn_junction.vtu")
