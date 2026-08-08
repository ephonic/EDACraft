"""Regression tests for equipotential multi-face FinFET/GAA gates."""

import numpy as np

from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device


def test_finfet_canonical_gate_biases_both_faces():
    dev = Device.finfet(Lg=12e-9, Lsd=8e-9, tsi=4e-9, Hfin=8e-9,
                        tox=2e-9, tgate=2e-9)
    mesh = structured_mesh_from_device(dev, resolution=(4e-9, 2e-9, 4e-9))
    sim = Simulator(mesh)
    sim.set_material_from_mesh()
    sim.set_contact("source", 0.0)
    sim.set_contact("drain", 0.0)
    sim.set_contact("gate", 0.7)
    result = sim.run(max_iter=100, tol=1e-6)
    assert result["converged"]
    for field in ("contact_gate", "contact_gate_r"):
        mask = mesh.fields[field].astype(bool).ravel()
        assert mask.any()
        assert np.allclose(result["phi"][mask], 0.7, atol=1e-12)


def test_gaa_template_exposes_four_gate_faces():
    dev = Device.gaa(Lg=12e-9, Lsd=8e-9, W_sheet=8e-9,
                     t_sheet=4e-9, tox=2e-9, t_gate=2e-9, t_box=4e-9)
    assert {"gate", "gate_b", "gate_l", "gate_r"}.issubset(dev.contacts)
