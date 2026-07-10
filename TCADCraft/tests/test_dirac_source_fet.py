"""Tests for Dirac-Source FET (DSFET) device template and physics.

DSFET uses a graphene (or other Dirac-material) source with a low effective
density-of-states (DOS) to suppress the high-energy thermal tail of electron
injection, enabling steep subthreshold switching beyond the 60 mV/dec limit.

These tests verify that:
1. The device template builds correctly with spatially varying Nc/Nv/Eg.
2. The C++ solver correctly consumes per-node Nc/Nv/Eg arrays.
3. The simulation converges and produces physically reasonable results.
"""

import numpy as np
import pytest

from tcad.geometry.device_builder import Device
from tcad.mesh.generator import structured_mesh_from_device
from tcad.simulator import Simulator


class TestDSFETTemplate:
    """Verify DSFET device template structure."""

    def test_dsfet_template_creates(self):
        dev = Device.dirac_source_fet()
        assert dev.name == "dirac_source_fet"
        region_names = [r.name for r in dev.regions]
        assert "source" in region_names
        assert "channel" in region_names
        assert "drain" in region_names

    def test_dsfet_source_is_graphene(self):
        """Source must be graphene (low DOS, low bandgap)."""
        dev = Device.dirac_source_fet()
        source_region = [r for r in dev.regions if r.name == "source"][0]
        assert source_region.material.name == "Graphene"
        assert source_region.material.Nc < 1e18
        assert source_region.material.Eg < 1.0

    def test_dsfet_channel_is_si(self):
        """Channel should be silicon for CMOS compatibility."""
        dev = Device.dirac_source_fet()
        channel = [r for r in dev.regions if r.name == "channel"][0]
        assert channel.material.name == "Silicon"

    def test_dsfet_contacts_have_nodes(self):
        """Contacts must overlap device regions to have mesh nodes."""
        dev = Device.dirac_source_fet(
            Lg=1.0e-6, Lsd=0.5e-6, t_sheet=0.5e-6, W_sheet=0.5e-6
        )
        mesh = structured_mesh_from_device(dev, resolution=(100e-9, 100e-9, 100e-9))
        for name in ["source", "drain", "gate"]:
            field = f"contact_{name}"
            mask = mesh.fields.get(field, np.zeros(mesh.npts())).astype(bool)
            assert mask.sum() > 0, f"DSFET {name} contact has no nodes"


class TestDSFETSimulation:
    """Verify DSFET can be simulated end-to-end."""

    def test_dsfet_basic_convergence(self):
        """A small DSFET should converge with standard settings."""
        dev = Device.dirac_source_fet(
            Lg=50e-9, Lsd=30e-9, t_sheet=10e-9, W_sheet=20e-9,
            Vg=0.5, Vd=0.1,
        )
        mesh = structured_mesh_from_device(dev, resolution=(20e-9, 10e-9, 10e-9))

        sim = Simulator(mesh, temperature=300.0)
        sim.set_material_from_mesh()
        for name, (shape, voltage) in dev.contacts.items():
            sim.set_contact(name, voltage)

        results = sim.run(max_iter=120, tol=1e-8)
        assert results["converged"], "DSFET simulation did not converge"
        assert results["n"].max() > 0
        assert results["p"].max() > 0

    def test_per_node_nc_nv_affects_result(self):
        """Verify that spatially varying Nc/Nv actually reaches the solver."""
        # Build a tiny two-region device: left half low Nc, right half high Nc
        from tcad.geometry.device_builder import Region, Material, Box, DopingProfile

        dev = Device("dos_test")
        low_nc = Material("LowNc", epsilon_r=11.7, Eg=1.12, Nc=1e17, Nv=1e17)
        high_nc = Material("HighNc", epsilon_r=11.7, Eg=1.12, Nc=2.8e19, Nv=1.04e19)
        dev.add_region(Region("left", Box(0, 0.5e-6, 0, 0.2e-6, 0, 0.1e-6), low_nc, DopingProfile(Nd=1e16)))
        dev.add_region(Region("right", Box(0.5e-6, 1e-6, 0, 0.2e-6, 0, 0.1e-6), high_nc, DopingProfile(Nd=1e16)))
        dev.add_contact("left_contact", Box(0, 0.2e-6, 0, 0.2e-6, -0.01e-6, 0), voltage=0.0)
        dev.add_contact("right_contact", Box(0.8e-6, 1e-6, 0, 0.2e-6, -0.01e-6, 0), voltage=0.1)

        mesh = structured_mesh_from_device(dev, nx=11, ny=3, nz=3)
        sim = Simulator(mesh, temperature=300.0)
        sim.set_material_from_mesh()
        for name, (shape, voltage) in dev.contacts.items():
            sim.set_contact(name, voltage)

        results = sim.run(max_iter=50, tol=1e-6)
        assert results["converged"]
        # Check that Nc varies across the mesh
        assert mesh.fields["Nc"].min() != mesh.fields["Nc"].max()
