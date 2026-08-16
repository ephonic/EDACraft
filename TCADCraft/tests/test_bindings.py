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

    def test_nonfinite_or_invalid_boundary_conditions_are_rejected(self):
        """Bad contact data must be rejected before it reaches Newton/Gummel."""
        sim = PyDeviceSimulator(3, 1, 1, 1.0, 1.0, 1.0)
        with pytest.raises(ValueError, match="potential boundary value"):
            sim.set_dirichlet_potential({0: np.nan})
        with pytest.raises(ValueError, match="electron boundary value"):
            sim.set_electron_bc({0: np.inf})
        with pytest.raises(ValueError, match="hole boundary value"):
            sim.set_hole_bc({0: -1.0})
        with pytest.raises(IndexError, match="outside the grid"):
            sim.set_dirichlet_potential({3: 0.0})

    def test_nonuniform_positions_are_validated(self):
        sim = PyDeviceSimulator(3, 1, 4, 1.0, 1.0, 1.0)
        sim.set_x_positions(np.array([0.0, 0.25, 1.0], dtype=float))
        sim.set_z_positions(np.array([0.0, 0.1, 0.4, 1.0], dtype=float))
        with pytest.raises(ValueError, match="position count mismatch"):
            sim.set_z_positions(np.array([0.0, 1.0], dtype=float))
        with pytest.raises(ValueError, match="strictly increasing"):
            sim.set_x_positions(np.array([0.0, 0.5, 0.5], dtype=float))

    def test_newton_poisson_uses_nonuniform_control_volume(self):
        """Newton and PoissonSolver must discretize the same Laplace operator."""
        positions = np.array([0.0, 1.0, 2.0, 4.0, 8.0]) * 1.0e-9
        sim = PyDeviceSimulator(5, 1, 1, 1.0e-9, 1.0, 1.0)
        sim.set_x_positions(positions)
        sim.set_permittivity(np.ones(5, dtype=float))
        sim.set_doping(np.zeros(5, dtype=float))
        sim.set_charge_volume_fraction(np.zeros(5, dtype=float))
        sim.set_mobility(np.ones(5, dtype=float), np.ones(5, dtype=float))
        sim.set_recombination(np.full(5, 1.0e100), np.full(5, 1.0e100))
        sim.set_effective_dos(np.ones(5), np.ones(5))
        sim.set_bandgap(np.zeros(5))
        sim.set_thermal_voltage(1.0)
        sim.set_dirichlet_potential({0: 0.0, 4: 1.0})
        # Zero-current Boltzmann contacts for a linear electrostatic ramp.
        sim.set_electron_bc({0: 1.0, 4: np.e})
        sim.set_hole_bc({0: 1.0, 4: 1.0 / np.e})
        sim.set_use_newton(True)
        sim.set_newton_primary(True)
        sim.set_newton_use_log_space(True)
        sim.set_gummel_max_iter(30)
        sim.set_tolerance(1.0e-8)
        result = sim.solve()
        assert result["converged"]
        assert result["phi"] == pytest.approx(positions / positions[-1], abs=1e-8)

    def test_newton_continuity_clips_insulator_half_cell_like_gummel(self):
        """Newton and Gummel must use one carrier CV at a material interface."""
        nx, nz = 5, 4
        size = nx * nz
        x_positions = np.arange(nx, dtype=float) * 1.0e-9
        z_positions = np.array([-5.0, 0.0, 1.0, 3.0]) * 1.0e-9
        mobility = np.ones(size, dtype=float)
        mobility[:nx] = 0.0  # oxide nodes above the shared interface row

        def configured_simulator():
            sim = PyDeviceSimulator(nx, 1, nz, 1.0e-9, 1.0, 1.0e-9)
            sim.set_x_positions(x_positions)
            sim.set_z_positions(z_positions)
            sim.set_permittivity(np.ones(size, dtype=float))
            sim.set_doping(np.zeros(size, dtype=float))
            sim.set_charge_volume_fraction(np.zeros(size, dtype=float))
            sim.set_mobility(mobility, mobility)
            sim.set_recombination(
                np.full(size, 1.0e100), np.full(size, 1.0e100)
            )
            sim.set_effective_dos(np.ones(size), np.ones(size))
            sim.set_bandgap(np.zeros(size))
            sim.set_thermal_voltage(1.0)
            sim.set_dirichlet_potential({index: 0.0 for index in range(size)})
            # Non-separable diffusion data makes the transverse/longitudinal
            # face-area ratio observable at the material-side interface row.
            electron_bc = {}
            for k in range(1, nz):
                electron_bc[nx * k] = 1.0
                electron_bc[nx * k + nx - 1] = 4.0
            for i in range(1, nx - 1):
                electron_bc[nx * (nz - 1) + i] = 1.0
            sim.set_electron_bc(electron_bc)
            sim.set_hole_bc({index: 1.0 for index in range(size)})
            sim.set_gummel_max_iter(80)
            sim.set_tolerance(1.0e-10)
            return sim

        gummel = configured_simulator()
        gummel.set_use_newton(False)
        reference = gummel.solve()
        assert reference["converged"]

        newton = configured_simulator()
        newton.set_initial_guess(
            np.asarray(reference["phi"]),
            np.asarray(reference["n"]),
            np.asarray(reference["p"]),
        )
        newton.set_use_newton(True)
        newton.set_newton_primary(True)
        newton.set_newton_use_log_space(True)
        result = newton.solve()
        assert result["converged"]
        assert result["n"] == pytest.approx(reference["n"], rel=1.0e-8, abs=1.0e-10)

    def test_charge_volume_fraction_is_validated(self):
        sim = PyDeviceSimulator(3, 1, 4, 1.0, 1.0, 1.0)
        sim.set_charge_volume_fraction(np.ones(12, dtype=float))
        with pytest.raises(ValueError, match="size mismatch"):
            sim.set_charge_volume_fraction(np.ones(11, dtype=float))
        invalid = np.ones(12, dtype=float)
        invalid[3] = 1.01
        with pytest.raises(ValueError, match=r"\[0,1\]"):
            sim.set_charge_volume_fraction(invalid)

    def test_density_gradient_coefficients_are_validated(self):
        sim = PyDeviceSimulator(3, 1, 1, 1.0, 1.0, 1.0)
        sim.set_density_gradient_coefficients(4.885e-20, 3.432e-20)
        with pytest.raises(ValueError, match="must be positive"):
            sim.set_density_gradient_coefficients(0.0, 3.432e-20)
        with pytest.raises(ValueError, match="must be positive"):
            sim.set_density_gradient_coefficients(np.inf, 3.432e-20)

    def test_silicon_multivalley_parameters_are_validated(self):
        sim = PyDeviceSimulator(3, 1, 3, 1.0, 1.0, 1.0)
        sim.set_density_gradient_silicon_multivalley(True, 0.916, 0.190, 4)
        with pytest.raises(ValueError, match="masses must be positive"):
            sim.set_density_gradient_silicon_multivalley(True, 0.0, 0.190, 4)
        with pytest.raises(ValueError, match=r"\[1,32\]"):
            sim.set_density_gradient_silicon_multivalley(True, 0.916, 0.190, 0)

    def test_density_gradient_interface_factor_is_validated(self):
        sim = PyDeviceSimulator(3, 1, 3, 1.0, 1.0, 1.0)
        sim.set_density_gradient_interface_distance_factor(0.6)
        with pytest.raises(ValueError, match="must be positive"):
            sim.set_density_gradient_interface_distance_factor(0.0)
        with pytest.raises(ValueError, match="must be positive"):
            sim.set_density_gradient_interface_distance_factor(np.inf)

    def test_density_gradient_potential_form_toggle(self):
        sim = PyDeviceSimulator(3, 1, 3, 1.0, 1.0, 1.0)
        sim.set_density_gradient_potential_form(True)
        sim.set_density_gradient_potential_form(False)

    def test_density_gradient_step_boundary_is_validated(self):
        sim = PyDeviceSimulator(3, 1, 3, 1.0, 1.0, 1.0)
        sim.set_density_gradient_step_boundary(
            True, 3.1727, 4.70314, 0.42, 1.0, 3.6, 5.6, 0.5, 0.5
        )
        with pytest.raises(ValueError, match="must be positive"):
            sim.set_density_gradient_step_boundary(
                True, 0.0, 4.70314, 0.42, 1.0, 3.6, 5.6, 0.5, 0.5
            )

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
        assert "poisson_residual" in results
        assert "quantum_residual" in results
