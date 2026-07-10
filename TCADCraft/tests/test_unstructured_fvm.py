"""Tests for unstructured FVM backend."""

import numpy as np
import pytest

from tcad.mesh.base import Mesh, Node, Element
from tcad.solver.unstructured_fvm import UnstructuredFVM
from tcad.solver.unstructured_simulator import UnstructuredSimulator


class TestUnstructuredFVM:
    def test_simple_tet_mesh_cv(self):
        """Control volumes should sum to total mesh volume."""
        mesh = Mesh()
        mesh.nodes = [Node(i, float(x), float(y), float(z)) for i, (x, y, z) in enumerate([
            (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1),
        ])]
        mesh.build_node_array()
        mesh.elements = [
            Element(0, [0, 1, 2, 3], "tetra"),
            Element(1, [1, 2, 3, 4], "tetra"),
        ]
        fvm = UnstructuredFVM(mesh)
        total_cv = fvm.cv.sum()
        expected_vol = 1.0 / 6.0 + 1.0 / 3.0  # 0.1667 + 0.3333
        assert total_cv == pytest.approx(expected_vol, rel=1e-6)

    def test_dirichlet_bc(self):
        """Dirichlet BC should be respected in the solution."""
        mesh = Mesh()
        mesh.nodes = [Node(i, float(x), float(y), float(z)) for i, (x, y, z) in enumerate([
            (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1),
        ])]
        mesh.build_node_array()
        mesh.elements = [
            Element(0, [0, 1, 2, 3], "tetra"),
            Element(1, [1, 2, 3, 4], "tetra"),
        ]
        fvm = UnstructuredFVM(mesh)
        fvm.set_dirichlet({0: 0.0, 4: 1.0})
        phi = fvm.solve_poisson()
        assert phi[0] == pytest.approx(0.0, abs=1e-10)
        assert phi[4] == pytest.approx(1.0, abs=1e-10)
        assert np.all(phi >= 0.0)
        assert np.all(phi <= 1.0)

    def test_electric_field_direction(self):
        """E-field should point from high to low potential."""
        mesh = Mesh()
        mesh.nodes = [Node(i, float(x), float(y), float(z)) for i, (x, y, z) in enumerate([
            (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1),
        ])]
        mesh.build_node_array()
        mesh.elements = [
            Element(0, [0, 1, 2, 3], "tetra"),
            Element(1, [1, 2, 3, 4], "tetra"),
        ]
        fvm = UnstructuredFVM(mesh)
        fvm.set_dirichlet({0: 0.0, 4: 1.0})
        phi = fvm.solve_poisson()
        Ex, Ey, Ez = fvm.compute_electric_field(phi)
        # At node 4 (high potential), E should point inward (negative components)
        assert Ex[4] < 0
        assert Ey[4] < 0
        assert Ez[4] < 0


class TestUnstructuredSimulator:
    def test_simulator_api(self):
        mesh = Mesh()
        mesh.nodes = [Node(i, float(x), float(y), float(z)) for i, (x, y, z) in enumerate([
            (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1),
        ])]
        mesh.build_node_array()
        mesh.elements = [
            Element(0, [0, 1, 2, 3], "tetra"),
            Element(1, [1, 2, 3, 4], "tetra"),
        ]
        # Add dummy contact field
        source_mask = np.zeros(5, dtype=float)
        source_mask[0] = 1.0
        drain_mask = np.zeros(5, dtype=float)
        drain_mask[4] = 1.0
        mesh.add_field("contact_source", source_mask)
        mesh.add_field("contact_drain", drain_mask)
        mesh.add_field("epsilon", np.ones(5) * 8.854e-12 * 11.7)
        mesh.add_field("doping", np.zeros(5))
        mesh.add_field("mu_n", np.ones(5) * 1400e-4)
        mesh.add_field("mu_p", np.ones(5) * 450e-4)

        sim = UnstructuredSimulator(mesh)
        sim.set_material_from_mesh()
        sim.set_contact("source", 0.0)
        sim.set_contact("drain", 1.0)
        results = sim.run()

        assert results["converged"]
        assert np.isclose(results["phi"][0], 0.0, atol=1e-10)
        assert np.isclose(results["phi"][4], 1.0, atol=1e-10)

    def test_to_mesh_fields(self):
        mesh = Mesh()
        mesh.nodes = [Node(i, float(x), float(y), float(z)) for i, (x, y, z) in enumerate([
            (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1),
        ])]
        mesh.build_node_array()
        mesh.elements = [
            Element(0, [0, 1, 2, 3], "tetra"),
            Element(1, [1, 2, 3, 4], "tetra"),
        ]
        mesh.add_field("epsilon", np.ones(5) * 8.854e-12 * 11.7)
        mesh.add_field("doping", np.zeros(5))
        mesh.add_field("mu_n", np.ones(5) * 1400e-4)
        mesh.add_field("mu_p", np.ones(5) * 450e-4)
        source_mask = np.zeros(5, dtype=float)
        source_mask[0] = 1.0
        mesh.add_field("contact_source", source_mask)

        sim = UnstructuredSimulator(mesh)
        sim.set_material_from_mesh()
        sim.set_contact("source", 0.0)
        sim._fvm.set_dirichlet({4: 1.0})
        sim.run()
        fields = sim.to_mesh_fields()
        assert "phi" in fields
        assert "Ex" in fields
        assert fields["phi"].shape == (5,)
