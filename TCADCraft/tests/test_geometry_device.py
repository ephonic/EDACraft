"""Tests for tcad.geometry.device_builder."""

import numpy as np
import pytest

from tcad.geometry.device_builder import (
    Device, Region, Material, DopingProfile, Box
)
from tcad.mesh.generator import structured_mesh_from_device


class TestMaterial:
    def test_defaults(self):
        m = Material("Silicon")
        assert m.epsilon_r == 11.7
        assert m.Eg == 1.12


class TestDopingProfile:
    def test_constant_doping(self):
        dp = DopingProfile(Nd=1e20, Na=0)
        x = np.array([0, 1, 2])
        result = dp.effective(x, x, x)
        np.testing.assert_array_equal(result, np.full(x.shape, 1e20, dtype=float))

    def test_functional_doping(self):
        dp = DopingProfile(
            Nd_func=lambda x, y, z: x * 1e20,
            Na=0
        )
        x = np.array([0.0, 0.5, 1.0])
        result = dp.effective(x, x, x)
        np.testing.assert_array_almost_equal(result, x * 1e20)


class TestDevice:
    def test_empty_bbox(self):
        dev = Device()
        assert dev.bbox() == ((0.0, 1.0), (0.0, 1.0), (0.0, 1.0))

    def test_bbox_from_regions(self):
        dev = Device()
        dev.add_region(Region("r1", Box(0, 2, 0, 3, 0, 4), Material("Si")))
        dev.add_region(Region("r2", Box(-1, 1, -1, 1, -1, 1), Material("Si")))
        assert dev.bbox() == ((-1, 2), (-1, 3), (-1, 4))

    def test_sample_on_grid(self):
        dev = Device()
        si = Material("Silicon", epsilon_r=11.7)
        dev.add_region(Region("bulk", Box(0, 1, 0, 1, 0, 1), si, DopingProfile(Nd=1e16)))
        x = np.array([0.5, 1.5])
        y = np.array([0.5, 0.5])
        z = np.array([0.5, 0.5])
        sampled = dev.sample_on_grid(x, y, z)
        assert sampled["material_id"][0] == 0
        assert sampled["material_id"][1] == -1  # outside
        assert sampled["epsilon"][0] == pytest.approx(11.7 * 8.854187817e-12)
        assert sampled["doping"][0] == pytest.approx(1e16)

    def test_painters_algorithm(self):
        """Later regions override earlier ones."""
        dev = Device()
        si = Material("Silicon", epsilon_r=11.7)
        ox = Material("Oxide", epsilon_r=3.9)
        dev.add_region(Region("bulk", Box(0, 2, 0, 2, 0, 2), si))
        dev.add_region(Region("oxide", Box(0, 1, 0, 1, 0, 1), ox))
        x = np.array([0.5, 1.5])
        y = np.array([0.5, 0.5])
        z = np.array([0.5, 0.5])
        sampled = dev.sample_on_grid(x, y, z)
        assert sampled["material_id"][0] == 1  # oxide overrides
        assert sampled["material_id"][1] == 0  # silicon
        assert sampled["epsilon"][0] == pytest.approx(3.9 * 8.854187817e-12)

    def test_get_contacts_on_grid(self):
        dev = Device()
        dev.add_contact("c1", Box(0, 1, 0, 1, 0, 1), voltage=0.5)
        x = np.array([0.5, 1.5])
        y = np.array([0.5, 0.5])
        z = np.array([0.5, 0.5])
        masks = dev.get_contacts_on_grid(x, y, z)
        assert masks["c1"][0]
        assert not masks["c1"][1]


class TestDeviceTemplates:
    def test_pnjunction(self):
        dev = Device.pnjunction()
        assert dev.name == "pn_junction"
        assert len(dev.regions) == 2
        assert "p_contact" in dev.contacts
        assert "n_contact" in dev.contacts

    def test_mosfet(self):
        dev = Device.mosfet()
        assert dev.name == "mosfet"
        assert len(dev.regions) >= 4
        assert "source" in dev.contacts
        assert "drain" in dev.contacts
        assert "gate" in dev.contacts

    def test_mosfet_custom_params(self):
        dev = Device.mosfet(Lg=100e-9, tox=2e-9, Vd=1.0)
        bbox = dev.bbox()
        x_total = 2 * 50e-9 + 100e-9  # Lsd defaults to 50e-9
        assert bbox[0][1] == pytest.approx(x_total)
        _, voltage = dev.contacts["drain"]
        assert voltage == 1.0

    def test_finfet(self):
        dev = Device.finfet()
        assert dev.name == "finfet"
        assert len(dev.regions) >= 6  # body, source, drain, 2 oxides, 2 metals
        assert "source" in dev.contacts
        assert "drain" in dev.contacts
        assert "gate" in dev.contacts

    def test_finfet_custom_params(self):
        dev = Device.finfet(Lg=50e-9, tox=2e-9, tsi=15e-9, Hfin=40e-9, Vg=0.8)
        bbox = dev.bbox()
        x_total = 2 * 30e-9 + 50e-9  # Lsd defaults to 30e-9
        assert bbox[0][1] == pytest.approx(x_total)
        _, voltage = dev.contacts["gate"]
        assert voltage == 0.8
    def test_gaa(self):
        dev = Device.gaa()
        assert dev.name == "gaa"
        assert len(dev.regions) >= 10  # substrate, box, channel, source, drain, 4 oxides, 4 metals
        assert "source" in dev.contacts
        assert "drain" in dev.contacts
        assert "gate" in dev.contacts

    def test_gaa_custom_params(self):
        dev = Device.gaa(Lg=30e-9, tox=2e-9, t_sheet=8e-9, W_sheet=40e-9, Vg=0.8)
        x_total = 2 * 30e-9 + 30e-9  # Lsd defaults to 30e-9
        bbox = dev.bbox()
        assert bbox[0][1] == pytest.approx(x_total)
        _, voltage = dev.contacts["gate"]
        assert voltage == 0.8

    def test_gaa_sampling(self):
        dev = Device.gaa()
        import numpy as np
        x = np.linspace(0, 80e-9, 30)
        y = np.linspace(-20e-9, 50e-9, 30)
        z = np.linspace(-30e-9, 30e-9, 30)
        X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
        sampled = dev.sample_on_grid(X.ravel(), Y.ravel(), Z.ravel())
        assert "epsilon" in sampled
        assert "doping" in sampled
        # Channel should be lightly doped p-type
        channel_mask = (X >= 30e-9) & (X <= 50e-9) & (Y >= 0) & (Y <= 30e-9) & (Z >= 0) & (Z <= 5e-9)
        channel_doping = sampled["doping"][channel_mask.ravel()]
        assert np.all(channel_doping < 0)  # Na > Nd => negative net doping

    def test_dirac_source_fet(self):
        dev = Device.dirac_source_fet()
        assert dev.name == "dirac_source_fet"
        assert len(dev.regions) >= 10
        assert "source" in dev.contacts
        assert "drain" in dev.contacts
        assert "gate" in dev.contacts
        region_names = [r.name for r in dev.regions]
        assert "source" in region_names
        assert "channel" in region_names
        assert "drain" in region_names

    def test_dirac_source_fet_graphene_source(self):
        dev = Device.dirac_source_fet()
        source_region = [r for r in dev.regions if r.name == "source"][0]
        assert source_region.material.name == "Graphene"
        assert source_region.material.Eg < 1.0  # Low/zero bandgap
        assert source_region.material.Nc < 1e18  # Low effective DOS

    def test_dirac_source_fet_si_channel(self):
        dev = Device.dirac_source_fet()
        channel_region = [r for r in dev.regions if r.name == "channel"][0]
        assert channel_region.material.name == "Silicon"
        assert channel_region.doping.Na > 0  # p-type / lightly doped

    def test_dirac_source_fet_custom_params(self):
        dev = Device.dirac_source_fet(Lg=30e-9, tox=2e-9, t_sheet=8e-9, W_sheet=40e-9, Vg=0.8)
        x_total = 2 * 30e-9 + 30e-9  # Lsd defaults to 30e-9
        bbox = dev.bbox()
        assert bbox[0][1] == pytest.approx(x_total)
        _, voltage = dev.contacts["gate"]
        assert voltage == 0.8

    def test_dirac_source_fet_contacts_have_nodes(self):
        dev = Device.dirac_source_fet(Lg=1.0e-6, Lsd=0.5e-6, t_sheet=0.5e-6, W_sheet=0.5e-6)
        mesh = structured_mesh_from_device(dev, resolution=(100e-9, 100e-9, 100e-9))
        for name in ["source", "drain", "gate"]:
            field = f"contact_{name}"
            mask = mesh.fields.get(field, np.zeros(mesh.npts())).astype(bool)
            assert mask.sum() > 0, f"DSFET {name} contact has no nodes"

    def test_sample_on_grid_includes_nc_nv(self):
        dev = Device()
        si = Material("Silicon", epsilon_r=11.7, Nc=2.8e19, Nv=1.04e19)
        dev.add_region(Region("bulk", Box(0, 1, 0, 1, 0, 1), si, DopingProfile(Nd=1e16)))
        x = np.array([0.5])
        y = np.array([0.5])
        z = np.array([0.5])
        sampled = dev.sample_on_grid(x, y, z)
        assert "Nc" in sampled
        assert "Nv" in sampled
        assert sampled["Nc"][0] == pytest.approx(2.8e19)
        assert sampled["Nv"][0] == pytest.approx(1.04e19)


