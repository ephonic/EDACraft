"""
Example: Adaptive mesh refinement for MOSFET simulation.
"""

import numpy as np
import tcad
from tcad.viz.plotter import plot_mesh_slice

# Build device
mosfet = tcad.Device.mosfet(
    Lg=50e-9, tox=1.5e-9, tsi=20e-9,
    W=100e-9, Lsd=50e-9,
    Vg=1.0, Vd=0.5, Vs=0.0,
)

# Uniform coarse mesh
coarse_mesh = tcad.generate_mesh(mosfet, method="structured", resolution=(5e-9, 10e-9, 2e-9))
print(f"Coarse mesh: {coarse_mesh.nx}x{coarse_mesh.ny}x{coarse_mesh.nz}")

# Feature-adaptive refined mesh
refiner = tcad.AdaptiveRefiner(mosfet, base_resolution=(5e-9, 10e-9, 2e-9))
refined_mesh = refiner.generate_feature_refined_mesh(level=2)
print(f"Refined mesh: {refined_mesh.nx}x{refined_mesh.ny}x{refined_mesh.nz}")

# Visualize doping on both meshes
plot_mesh_slice(coarse_mesh, field="doping", axis="z", coord=10e-9)
plot_mesh_slice(refined_mesh, field="doping", axis="z", coord=10e-9)

# Simulate on refined mesh
sim, results = tcad.simulate_device(
    mosfet,
    resolution=(5e-9, 10e-9, 2e-9),
    adaptive_level=2,
    temperature=300.0,
    quantum=True,
    max_iter=30,
    tol=1e-8,
)

print(f"Converged: {results['converged']}, Iterations: {results['iterations']}")

# Attach results and visualize
fields = sim.to_mesh_fields()
for name, data in fields.items():
    sim.mesh.add_field(name, data.ravel())

plot_mesh_slice(sim.mesh, field="phi", axis="y", coord=50e-9)
sim.save("adaptive_mosfet.vtu")
print("Saved to adaptive_mosfet.vtu")
