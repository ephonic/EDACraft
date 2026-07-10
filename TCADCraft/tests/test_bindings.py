"""Tests for the Cython/C++ binding layer."""

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator


class TestPyDeviceSimulator:
    def test_init(self):
        sim = PyDeviceSimulator(5, 5, 5, 1.0, 1.0, 1.0)
        assert sim is not None

    def test_set_doping(self):
        sim = PyDeviceSimulator(3, 3, 3, 1.0, 1.0, 1.0)
        doping = np.ones(27, dtype=float)
        sim.set_doping(doping)

    def test_set_permittivity(self):
        sim = PyDeviceSimulator(3, 3, 3, 1.0, 1.0, 1.0)
        eps = np.full(27, 11.7 * 8.854e-12, dtype=float)
        sim.set_permittivity(eps)

    def test_set_mobility(self):
        sim = PyDeviceSimulator(3, 3, 3, 1.0, 1.0, 1.0)
        mu_n = np.full(27, 1400e-4, dtype=float)
        mu_p = np.full(27, 450e-4, dtype=float)
        sim.set_mobility(mu_n, mu_p)

    def test_dirichlet_bc(self):
        sim = PyDeviceSimulator(3, 3, 3, 1.0, 1.0, 1.0)
        bc = {0: 0.0, 1: 1.0}
        sim.set_dirichlet_potential(bc)

    def test_solve_trivial(self):
        """Solve on a tiny grid with trivial boundary conditions."""
        sim = PyDeviceSimulator(3, 3, 3, 1.0, 1.0, 1.0)
        sim.set_doping(np.zeros(27, dtype=float))
        sim.set_permittivity(np.ones(27, dtype=float))
        sim.set_mobility(np.ones(27, dtype=float), np.ones(27, dtype=float))
        sim.set_thermal_voltage(0.02585)
        bc = {0: 0.0}
        sim.set_dirichlet_potential(bc)
        sim.set_electron_bc({0: 1e16})
        sim.set_hole_bc({0: 1e16})
        sim.set_gummel_max_iter(5)
        sim.set_tolerance(1e-4)
        results = sim.solve()
        assert "phi" in results
        assert results["converged"] in [True, False]
        assert results["iterations"] >= 0
