"""Independent quadrature and protocol tests for spatial FE readout."""
from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from tcad.mesh.structured_grid import StructuredGrid
from tcad.postprocess import polarization_readout
from tcad.postprocess.fe_loops import (
    _read_axial_polarization, run_pv_sweep, run_pund_sequence,
    run_retention, run_endurance, run_pulse_width_sweep,
)
from test_fe_measurement_protocols import IdealFE
from test_physical_step_commit import high_level


def explicit_mesh(volumes, **fields):
    return SimpleNamespace(npts=lambda: len(volumes),
                           fields={"control_volume": np.array(volumes), **fields})


def axial(values, axis=0):
    P = np.zeros((len(values), 3))
    P[:, axis] = values
    return P


@pytest.mark.parametrize("shape", [(1, 1, 1), (5, 1, 1), (1, 4, 1),
                                  (1, 1, 3), (3, 4, 1), (3, 4, 5)])
def test_volume_sum_and_multilinear_integral(shape):
    # Analytic integral over [1,3] x [2,5] x [-2,2], including extrusion axes.
    mesh = StructuredGrid(((1., 3.), (2., 5.), (-2., 2.)), *shape)
    volume = mesh.control_volumes()
    assert volume.sum() == pytest.approx(24.)
    x, y, z = mesh.flat_coords()
    # Singleton coordinates are at the low endpoint; use an axis-constant
    # field there, because a single node cannot resolve an axial variation.
    x = x if shape[0] > 1 else np.full_like(x, 2.)
    y = y if shape[1] > 1 else np.full_like(y, 3.5)
    z = z if shape[2] > 1 else np.zeros_like(z)
    P = axial(2 + x*y + x*z + y*z + x*y*z)
    out = polarization_readout(P, mesh)
    assert out["mean_polarization"] == pytest.approx(9.)
    assert out["fe_volume_m3"] == pytest.approx(24.)
    # Check individual volumes without using the implementation's reshape.
    for k in range(shape[2]):
        for j in range(shape[1]):
            for i in range(shape[0]):
                expected = 1.
                for index, count, span in zip((i, j, k), shape, (2., 3., 4.)):
                    expected *= (span if count == 1 else span/(count-1)
                                 * (.5 if index in (0, count-1) else 1.))
                assert volume[mesh.index(i, j, k)] == pytest.approx(expected)


@pytest.mark.parametrize("nodes", [5, 9, 17])
def test_quadratic_integral_has_trapezoid_error_not_node_count_bias(nodes):
    mesh = StructuredGrid(((0., 1.), (0., 2.), (0., 3.)), nodes, 1, 1)
    x = mesh.flat_coords()[0]
    out = polarization_readout(axial(x*x), mesh)
    expected = 1/3 + 1/(6*(nodes-1)**2)
    assert out["mean_polarization"] == pytest.approx(expected, abs=1e-15)
    assert out["fe_volume_m3"] == pytest.approx(6.)
    assert abs(out["mean_polarization"]-1/3) < abs(np.mean(x*x)-1/3)


def test_nonuniform_piecewise_linear_field_invariant_under_node_insertion():
    # Independent 1D trapezoid integration: inserting points on the existing
    # linear segments leaves the integral unchanged; node means do not.
    means = []
    for x in (np.array([0., .1, 1.]), np.array([0., .05, .1, .55, 1.])):
        values = np.interp(x, [0., .1, 1.], [0., 1., 0.])
        edges = np.r_[x[0], (x[:-1]+x[1:])/2, x[-1]]
        mesh = explicit_mesh(6*np.diff(edges))
        out = polarization_readout(axial(values), mesh)
        assert out["mean_polarization"] == pytest.approx(.5)
        assert out["fe_volume_m3"] == pytest.approx(6.)
        means.append(np.mean(values))
    assert means == pytest.approx([1/3, .4])


def test_FE_cell_fraction_and_signed_domain_cancellation():
    mesh = explicit_mesh([1., 2., 4., 8.], fe_alpha=[-1., -1., -1., 0.],
                         fe_volume_fraction=[1., .5, .25, 1.])
    out = polarization_readout(axial([.2, -.2, .2, 1000.]), mesh)
    assert out["mean_polarization"] == pytest.approx(.2/3)
    assert out["mean_absolute_polarization"] == pytest.approx(.2)
    assert out["min_polarization"] == -.2
    assert out["max_polarization"] == .2
    assert out["fe_volume_m3"] == 3.
    assert out["contributing_nodes"] == 3
    assert out["interface_geometry"] == "explicit_FE_volume_fraction"
    assert out["physical_validated"] is False
    assert out["terminal_charge_validated"] is False


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_axis_and_flat_polarization_and_mesh_order_permutation(axis):
    volumes, values = np.array([1., 2., 4.]), np.array([-.2, .1, .2])
    for order in ([0, 1, 2], [2, 0, 1]):
        out = polarization_readout(axial(values[order], axis).ravel(),
                                   explicit_mesh(volumes[order]), polar_axis=axis)
        assert out["mean_polarization"] == pytest.approx(.8/7)
        assert out["polarization_units"] == "C/m^2"


@pytest.mark.parametrize("axis", [-1, 3, .5, 0., True, "0"])
def test_reject_invalid_axis(axis):
    with pytest.raises(ValueError):
        polarization_readout(axial([1., 2.]), explicit_mesh([1., 1.]), polar_axis=axis)


@pytest.mark.parametrize("field, value", [
    ("control_volume", [0., 1.]), ("control_volume", [-1., 1.]),
    ("control_volume", [np.inf, 1.]), ("control_volume", [np.nan, 1.]),
    ("control_volume", [1.]), ("control_volume", [1e308, 1e308]),
    ("fe_volume_fraction", [-.1, 1.]), ("fe_volume_fraction", [1.1, 1.]),
    ("fe_volume_fraction", [np.nan, 1.]), ("fe_volume_fraction", [1.]),
    ("fe_volume_fraction", [0., 0.]), ("fe_alpha", [0., 0.]),
    ("fe_alpha", [np.nan, -1.]), ("fe_alpha", [-1.]),
])
def test_reject_invalid_geometry_before_reporting_a_measurement(field, value):
    mesh = explicit_mesh([1., 1.])
    mesh.fields[field] = value
    with pytest.raises(ValueError):
        polarization_readout(axial([.1, .2]), mesh)


@pytest.mark.parametrize("mask", [[0, 0], [1, 2], [1, np.nan], [1]])
def test_reject_bad_or_empty_FE_mask(mask):
    with pytest.raises(ValueError):
        polarization_readout(axial([.1, .2]), explicit_mesh([1., 1.]), fe_mask=mask)


@pytest.mark.parametrize("P", [np.zeros((1, 3)), np.zeros((3, 2)),
                              axial([np.nan, .2]), axial([np.inf, .2])])
def test_reject_invalid_polarization(P):
    with pytest.raises(ValueError):
        polarization_readout(P, explicit_mesh([1., 1.]))


def test_no_silent_equal_node_fallback_and_no_charge_fraction_reuse():
    mesh = SimpleNamespace(npts=lambda: 2, fields={})
    with pytest.raises(ValueError, match="control volumes"):
        polarization_readout(axial([.1, .2]), mesh)
    mesh.fields = {"control_volume": [1., 2.], "charge_volume_fraction": [0., 1.]}
    # Poisson's charge correction is not the geometric FE-volume fraction.
    assert polarization_readout(axial([.1, .2]), mesh)["mean_polarization"] == pytest.approx(1/6)


def test_positive_FE_volume_underflow_is_rejected():
    mesh = explicit_mesh([1e-300, 1e-300], fe_volume_fraction=[1e-300, 1.])
    with pytest.raises(ValueError, match="underflow"):
        polarization_readout(axial([.1, .2]), mesh)


class SpatialFE(IdealFE):
    def __init__(self):
        super().__init__(ps=.2, susceptibility=0.)
        self.mesh.fields = {"control_volume": np.array([.5, 1., 1., .5]),
                            "fe_alpha": np.ones(4)}

    def run(self, **kwargs):
        result = super().run(**kwargs)
        # Only the boundary dual cells switch. Their combined volume is 1/3
        # of the domain; arithmetic node averaging would incorrectly give 1/2.
        result["P"][1:3, 2] = 0.
        return result


@pytest.mark.parametrize("driver", ["pv", "pund", "retention", "endurance", "width"])
def test_protocols_use_volume_weighted_spatial_polarization(driver):
    sim = SpatialFE()
    if driver == "pv":
        _, values, result = run_pv_sweep(sim, "gate", 2., n_pts=2)
        assert max(abs(values)) == pytest.approx(.2/3)
        assert result["fe_polarization_readout"]["fe_volume_m3"] == 3.
    elif driver == "pund":
        out = run_pund_sequence(sim, "gate", 2., 1e-8, n_points=10, pre_pol_hold=1)
        assert out["P_switch_positive"] == pytest.approx(.4/3)
        assert out["P_switch_negative"] == pytest.approx(-.4/3)
        assert out["Pr"] == pytest.approx(.2/3)
    elif driver == "retention":
        out = run_retention(sim, "gate", 2., n_steps=2)
        assert out["P_initial"] == pytest.approx(.2/3)
        assert out["P_final"] == pytest.approx(.2/3)
    elif driver == "endurance":
        out = run_endurance(sim, "gate", 2., 1e-8, n_cycles=2, measure_every=1)
        np.testing.assert_allclose(out["Ps"], .2/3)
    else:
        out = run_pulse_width_sweep(sim, "gate", 2., 1e-8,
                                   pulse_widths=[.2], saturation_polarization=.2)
        assert out["Ps"][0] == pytest.approx(.2/3)
        assert out["memory_window"][0] == pytest.approx(4/3)
    if driver != "pv":
        assert out["polarization_weighting"] == "FE_control_volume"


def test_bad_geometry_rolls_back_native_pv_physical_segment():
    sim = high_level()
    assert sim.run(max_iter=300, tol=1e-8)["converged"]
    saved = deepcopy(sim.results)
    contacts = deepcopy(sim._contact_voltages)
    sim.mesh.fields["control_volume"] = np.zeros(sim.mesh.npts())
    with pytest.raises(RuntimeError) as error:
        run_pv_sweep(sim, "right", 4., n_pts=2, max_iter=300, tol=1e-8)
    assert error.value.completed_segments == 0
    assert sim._contact_voltages == contacts
    np.testing.assert_array_equal(sim.results["P"], saved["P"])
    # Also verify hidden NLS memory, after removing the bad diagnostic input.
    del sim.mesh.fields["control_volume"]
    reference = high_level()
    assert reference.run(max_iter=300, tol=1e-8)["converged"]
    for target in [4., -4., 4.]:
        sim.update_contact("right", target)
        reference.update_contact("right", target)
        np.testing.assert_allclose(sim.run(physical_step=True)["P"],
                                   reference.run(physical_step=True)["P"], atol=1e-12)


def test_native_spatial_readout_matches_independent_cell_integral():
    sim = high_level(initial_voltage=4.)
    result = sim.run(max_iter=300, tol=1e-8, physical_step=True)
    x = sim.mesh.flat_coords()[0]
    # Direct element integral from adjacent nodal values, independent of the
    # new volume API and the public readout's dot-product implementation.
    values = result["P"][:, sim._fe_polar_axis]
    expected = np.sum(np.diff(x)*(values[:-1]+values[1:])/2)/(x[-1]-x[0])
    assert _read_axial_polarization(sim, result) == pytest.approx(expected, abs=1e-15)


def test_configured_FE_mask_overrides_material_domain_and_is_owned():
    sim = high_level()
    count = sim.mesh.npts()
    sim.mesh.fields.update(fe_alpha=np.full(count, -5e8),
                           fe_beta=np.full(count, 1.25e10))
    mask = np.zeros(count, dtype=np.int8)
    mask[1:3] = 1
    sim.set_ferroelectric(model="nls", Ps=.2, Ec=1e8, polar_axis="x",
                          fe_mask_override=mask)
    mask[:] = 0  # Mutating the caller's buffer must not change the domain.
    result = {"P": axial([0., .2, .2] + [0.]*(count-3))}
    assert _read_axial_polarization(sim, result) == pytest.approx(.2)
    assert result["fe_polarization_readout"]["contributing_nodes"] == 2
    sim.set_ferroelectric(enabled=False, model="nls", polar_axis="x")
    with pytest.raises(ValueError, match="positive FE volume"):
        _read_axial_polarization(sim, result)


@pytest.mark.parametrize("mask", [[1], [1, np.nan], [1, 256], [1, .5]])
def test_bad_override_mask_is_rejected_before_native_configuration(mask):
    sim = high_level()
    saved = sim._fe_node_mask.copy()
    if len(mask) == 2:
        mask = mask + [0] * (sim.mesh.npts()-2)
    with pytest.raises(ValueError, match="fe_mask_override"):
        sim.set_ferroelectric(model="preisach", fe_mask_override=mask)
    assert sim._fe_model_int == 2
    np.testing.assert_array_equal(sim._fe_node_mask, saved)
