"""Tests for tcad.mesh.generator."""

import numpy as np
import pytest

from tcad.mesh.generator import structured_mesh_from_device
from tcad.geometry.device_builder import Device


class TestStructuredMeshFromDevice:
    def test_resolution(self):
        dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
        mesh = structured_mesh_from_device(dev, resolution=(0.5e-6, 0.5e-6, 0.5e-6))
        # bbox is ((0, 1e-6), (0, 1e-6), (-0.01e-6, 1e-6))
        # nx = max(3, int(1e-6 / 0.5e-6) + 1) = 3
        assert mesh.nx >= 3
        assert mesh.ny >= 3
        assert mesh.nz >= 3
        assert "doping" in mesh.fields
        assert "contact_p_contact" in mesh.fields
        assert "contact_n_contact" in mesh.fields

    def test_explicit_counts(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=7, ny=8, nz=9)
        assert mesh.nx == 7
        assert mesh.ny == 8
        assert mesh.nz == 9

    def test_default_counts(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev)
        assert mesh.nx == 51
        assert mesh.ny == 51
        assert mesh.nz == 51

    def test_doping_values(self):
        dev = Device.pnjunction(x_junction=0.5e-6, Na=1e18, Nd=1e17)
        mesh = structured_mesh_from_device(dev, nx=11, ny=3, nz=3)
        doping = mesh.fields["doping"]
        # Node-ordered flat coordinates (i fastest) — §19.
        fx, _, _ = mesh.flat_coords()
        # Find points on p-side (x < 0.5e-6) and n-side (x > 0.5e-6)
        p_side = doping[fx < 0.4e-6]
        n_side = doping[fx > 0.6e-6]
        assert np.all(p_side < 0)  # Na > Nd -> net negative (p-type)
        assert np.all(n_side > 0)  # n-type
