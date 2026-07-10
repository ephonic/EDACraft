"""Tests for tcad.mesh.structured_grid."""

import numpy as np
import pytest

from tcad.mesh.structured_grid import StructuredGrid
from tcad.geometry.device_builder import Device, Region, Material, Box


class TestStructuredGrid:
    def test_shape_and_npts(self):
        grid = StructuredGrid(((0, 1), (0, 1), (0, 1)), 3, 4, 5)
        assert grid.shape() == (3, 4, 5)
        assert grid.npts() == 3 * 4 * 5

    def test_spacing(self):
        grid = StructuredGrid(((0, 2), (0, 4), (0, 6)), 3, 3, 3)
        assert grid.dx == pytest.approx(1.0)
        assert grid.dy == pytest.approx(2.0)
        assert grid.dz == pytest.approx(3.0)

    def test_index_roundtrip(self):
        grid = StructuredGrid(((0, 1), (0, 1), (0, 1)), 4, 5, 6)
        for k in range(grid.nz):
            for j in range(grid.ny):
                for i in range(grid.nx):
                    idx = grid.index(i, j, k)
                    assert grid.ijk(idx) == (i, j, k)

    def test_node_coords(self):
        grid = StructuredGrid(((0, 1), (0, 1), (0, 1)), 2, 2, 2)
        grid.build_node_array()
        assert grid.node_coords.shape == (8, 3)
        # Corner check
        np.testing.assert_array_almost_equal(grid.node_coords[0], [0, 0, 0])
        np.testing.assert_array_almost_equal(grid.node_coords[-1], [1, 1, 1])

    def test_to_cxx_grid(self):
        grid = StructuredGrid(((0, 3), (0, 4), (0, 5)), 4, 5, 6)
        g = grid.to_cxx_grid()
        assert g["nx"] == 4
        assert g["ny"] == 5
        assert g["nz"] == 6
        assert g["dx"] == pytest.approx(1.0)
        assert g["dy"] == pytest.approx(1.0)
        assert g["dz"] == pytest.approx(1.0)

    def test_create_device_fields(self):
        dev = Device.pnjunction()
        grid = StructuredGrid(dev.bbox(), 5, 5, 5)
        fields = grid.create_device_fields(dev)
        assert "material_id" in fields
        assert "epsilon" in fields
        assert "doping" in fields
        assert fields["material_id"].shape == (5 * 5 * 5,)

    def test_contact_masks(self):
        dev = Device.pnjunction()
        grid = StructuredGrid(dev.bbox(), 11, 11, 11)
        masks = grid.contact_masks(dev)
        assert "p_contact" in masks
        assert "n_contact" in masks
        # At least some points should be inside each contact
        assert masks["p_contact"].sum() > 0
        assert masks["n_contact"].sum() > 0

    def test_add_field_size_mismatch(self):
        grid = StructuredGrid(((0, 1), (0, 1), (0, 1)), 2, 2, 2)
        with pytest.raises(ValueError):
            grid.add_field("test", np.zeros(7))
