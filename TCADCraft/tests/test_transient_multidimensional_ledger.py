"""Audit nonzero BE diffusion against an independent finite-volume system."""

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator, native_constants
from tcad.validation.conservation import TransientConservationTest


QE = float(native_constants()["elementary_charge_C"])
DIFFUSIVITY = .1 * .025852


def experiment(shape, planes, stretched=False, final=2.5e-10):
    nx, ny, nz = shape
    size = nx * ny * nz
    spacings = np.array([1., 1.3, .8]) * 1e-6
    axes = [np.arange(count) * spacing for count, spacing in zip(shape, spacings)]
    if stretched:
        axes = [x * (1 + .12 * np.arange(len(x))) for x in axes]
    widths = []
    for x, spacing in zip(axes, spacings):
        edge = np.diff(x)
        widths.append(np.r_[edge[0], (edge[:-1] + edge[1:]) / 2, edge[-1]]
                      if len(x) > 1 else np.array([spacing]))
    sim = PyDeviceSimulator(nx, ny, nz, *spacings)
    sim.set_newton_freeze_phi(True)  # Independent diffusion matrix assumes E=0.
    for axis, setter in zip(axes, [sim.set_x_positions, sim.set_y_positions, sim.set_z_positions]):
        setter(axis)
    sim.set_permittivity(np.full(size, 8.854187817e-12 * 11.7))
    sim.set_mobility(np.full(size, .1), np.full(size, .05))
    sim.set_doping(np.zeros(size))
    sim.set_effective_dos(np.full(size, 1e16), np.full(size, 1e16))
    sim.set_bandgap(np.zeros(size))
    sim.set_recombination(np.full(size, 1e100), np.full(size, 1e100))
    sim.set_thermal_voltage(.025852)
    # Curved contact concentrations produce nonzero contact-to-contact flux.
    # A linear boundary profile could accidentally cancel that bookkeeping bug.
    coords = np.array([(i, j, k) for k in range(nz) for j in range(ny) for i in range(nx)])
    contacts = np.zeros(size, dtype=bool)
    for axis, upper in planes:
        contacts |= coords[:, axis] == (shape[axis] - 1 if upper else 0)
    density = 1e16 * (1 + .03 * (coords ** 2 @ np.array([1., 2., 3.])))
    density[~contacts] += 3e15
    hole_density = 1e16 * (1 + .02 * (coords ** 2 @ np.array([3., 1., 2.])))
    hole_density[~contacts] += 1e15
    nbc = {int(idx): float(density[idx]) for idx in np.flatnonzero(contacts)}
    sim.set_electron_bc(nbc)
    sim.set_hole_bc({idx: float(hole_density[idx]) for idx in nbc})
    sim.set_dirichlet_potential({idx: 0. for idx in nbc})
    sim.set_initial_guess(np.zeros(size), density, hole_density)
    sim.set_gummel_max_iter(80)
    sim.set_tolerance(1e-10)
    sim.set_transient_dt(1e-10)
    sim.set_transient_t_final(final)
    return sim, coords, axes, widths, contacts, density, hole_density


def independent_operator(shape, coords, axes, widths, contacts):
    """Positive -D*Laplacian; contact rows are imposed separately for BE."""
    strides = [1, shape[0], shape[0] * shape[1]]
    matrix = np.zeros((len(coords), len(coords)))
    for idx, xyz in enumerate(coords):
        if contacts[idx]:
            continue
        for axis in range(3):
            position = xyz[axis]
            for sign in (-1, 1):
                neighbor = position + sign
                if 0 <= neighbor < shape[axis]:
                    coefficient = DIFFUSIVITY / (
                        abs(axes[axis][neighbor] - axes[axis][position]) * widths[axis][position])
                    matrix[idx, idx] += coefficient
                    matrix[idx, idx + sign * strides[axis]] -= coefficient
    return matrix


CASES = [
    ((5, 4, 1), [(0, False), (0, True)]),
    ((5, 4, 1), [(1, False), (1, True)]),
    ((5, 4, 1), [(0, False), (1, False)]),
    ((5, 4, 1), [(0, False), (0, True), (1, False), (1, True)]),
    ((5, 4, 3), [(0, False), (0, True)]),
    ((5, 4, 3), [(2, False), (2, True)]),
    ((5, 4, 3), [(axis, upper) for axis in range(3) for upper in (False, True)]),
    ((1, 5, 1), [(1, False), (1, True)]),
    ((1, 1, 5), [(2, False), (2, True)]),
]


@pytest.mark.parametrize("shape,planes", CASES)
@pytest.mark.parametrize("stretched", [False, True])
def test_nonzero_multidimensional_be_and_contact_fluxes(shape, planes, stretched):
    sim, coords, axes, widths, contacts, expected_n, expected_p = experiment(shape, planes, stretched)
    history = sim.solve_transient()
    operator = independent_operator(shape, coords, axes, widths, contacts)
    volume = np.prod(np.array([widths[a][coords[:, a]] for a in range(3)]), axis=0)
    strides = [1, shape[0], shape[0] * shape[1]]
    assert len(history) == 4
    for state in history:
        assert state["converged"] and state["valid"] and state["charge_ledger_available"]
        matrix = np.eye(len(coords)) + state["dt_s"] * operator
        expected_n = np.linalg.solve(matrix, expected_n)
        expected_p = np.linalg.solve(np.eye(len(coords)) + state["dt_s"] * .5 * operator, expected_p)
        np.testing.assert_allclose(state["n"], expected_n, rtol=2e-7)
        np.testing.assert_allclose(state["p"], expected_p, rtol=2e-7)
        charge = QE * np.dot(state["p"][~contacts] - state["n"][~contacts], volume[~contacts])
        assert state["stored_charge_C"] == pytest.approx(charge, rel=1e-12)
        currents = []
        for axis, upper in sorted(planes):
            coordinate = shape[axis] - 2 if upper else 0
            current = 0.
            for idx in np.flatnonzero(coords[:, axis] == coordinate):
                neighbor = idx + strides[axis]
                # Only edges connecting the external reservoir to a free node
                # belong to the balance of free-node storage.
                if contacts[idx] == contacts[neighbor]:
                    continue
                area = np.prod([widths[a][coords[idx, a]] for a in range(3) if a != axis])
                edge = abs(axes[axis][coords[neighbor, axis]] - axes[axis][coords[idx, axis]])
                electron = QE * DIFFUSIVITY * (state["n"][neighbor] - state["n"][idx]) / edge
                hole = -QE * .05 * .025852 * (state["p"][neighbor] - state["p"][idx]) / edge
                current += (-1 if upper else 1) * area * (electron + hole)
            currents.append(current)
        np.testing.assert_allclose(state["terminal_currents_A"], currents, rtol=2e-10, atol=1e-28)
    verdict = TransientConservationTest(integration="backward_euler", charge_atol_C=0.,
                                       tolerance=1e-5).run(lambda: history)
    assert verdict.passed, verdict.message


@pytest.mark.parametrize("node", [0, 6])
def test_poisson_cut_cell_fraction_cannot_claim_transport_charge_closure(node):
    sim, *_ = experiment(*CASES[0])
    fraction = np.ones(20)
    fraction[node] = .4
    sim.set_charge_volume_fraction(fraction)
    history = sim.solve_transient()
    assert all(state["converged"] for state in history)
    assert not any(state["charge_ledger_available"] for state in history)
    assert not any("stored_charge_C" in state for state in history)
    assert not TransientConservationTest(integration="backward_euler").run(lambda: history).passed


@pytest.mark.parametrize("carrier", ["electron", "hole"])
def test_inactive_contact_geometry_cannot_claim_full_volume_ledger(carrier):
    sim, _, _, _, contacts, _, _ = experiment(*CASES[1], final=0.)
    electron, hole = np.full(20, .1), np.full(20, .05)
    (electron if carrier == "electron" else hole)[np.flatnonzero(contacts)[1]] = 0.
    sim.set_mobility(electron, hole)
    assert not sim.solve_transient()[0]["charge_ledger_available"]


def test_no_free_control_volumes_do_not_claim_device_charge_ledger():
    sim, *_ = experiment((2, 3, 1), [(0, False), (0, True)], final=0.)
    assert not sim.solve_transient()[0]["charge_ledger_available"]
