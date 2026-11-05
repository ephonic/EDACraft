"""Charge continuity and energy accounting, independently prescribed ledgers."""

from types import SimpleNamespace

import numpy as np
import pytest

from tcad.validation.conservation import ConservationTest, TransientConservationTest


def steady(**fields):
    return ConservationTest(check_energy=False).run(
        lambda: {"converged": True, **fields})


def snapshot(time, charge, currents=(1e-9, 0.0)):
    return dict(time_s=time, stored_charge_C=charge,
                terminal_currents_A=currents, converged=True)


def test_doped_device_with_balanced_contacts_needs_no_carrier_neutrality():
    result = steady(n=[1e23, 1e23], p=[1e10, 1e10],
                    terminal_currents_A={"source": 2e-6, "drain": -2e-6})
    assert result.passed


def test_neutral_carriers_do_not_hide_a_current_leak():
    result = steady(n=[1e20, 1e20], p=[1e20, 1e20],
                    terminal_currents_A=[2e-6, -1e-6])
    assert not result.passed
    assert result.details["status"] == "failed"


@pytest.mark.parametrize("currents", [None, [], [0.0], [1.0, np.nan], [[1.0], [-1.0]]])
def test_missing_or_malformed_contact_currents_fail(currents):
    assert not steady(n=[0.0], p=[0.0], terminal_currents_A=currents).passed


def test_equilibrium_currents_use_explicit_si_absolute_budget():
    assert steady(terminal_currents_A=[2e-16, 0.0]).passed
    assert not steady(terminal_currents_A=[2e-12, 0.0]).passed


def test_object_access_and_extractor_use_same_kcl_contract():
    state = SimpleNamespace(converged=True)
    check = ConservationTest(check_energy=False,
        current_extractor=lambda sim, result: {"left": 3e-6, "right": -3e-6})
    assert check.run(lambda: state).passed


@pytest.mark.parametrize("status", [{}, {"converged": "False"}, {"valid": np.nan},
                                     {"converged": False}])
def test_absent_or_invalid_solver_status_cannot_pass(status):
    check = ConservationTest(check_energy=False)
    assert not check.run(lambda: dict(terminal_currents_A=[0.0, 0.0], **status)).passed


def test_energy_ledger_counts_external_work():
    check = ConservationTest(check_charge=False)
    state = dict(converged=True, energy_initial=2e-12, energy_supplied=5e-12,
                 energy_final=4e-12, energy_dissipated=3e-12)
    assert check.run(lambda: state).passed
    state["energy_supplied"] = 4e-12
    assert not check.run(lambda: state).passed


def test_energy_ledger_accepts_explicit_storage_components():
    check = ConservationTest(check_charge=False)
    state = dict(converged=True,
        energy_components_initial_J={"dielectric": 2e-12, "polarization": 1e-12},
        energy_components_final_J={"dielectric": 1e-12, "polarization": 1e-12},
        energy_components_supplied_J={"source": 0.0},
        energy_components_dissipated_J={"leakage": 1e-12})
    assert check.run(lambda: state).passed
    state["energy_components_final_J"]["trap"] = 0.0
    assert not check.run(lambda: state).passed


@pytest.mark.parametrize("bad", [None, {"polarization": np.nan},
                                   {"polarization": [1e-12, 2e-12]}, {1: 1e-12}])
def test_invalid_energy_component_ledger_cannot_be_treated_as_zero(bad):
    state = dict(converged=True, energy_components_initial_J=bad,
                 energy_components_final_J={"polarization": 1e-12})
    assert not ConservationTest(check_charge=False).run(lambda: state).passed


@pytest.mark.parametrize("name", ["energy_supplied", "energy_dissipated"])
def test_invalid_energy_term_is_not_silently_zero(name):
    state = dict(converged=True, energy_initial=1.0, energy_final=1.0)
    state[name] = np.nan
    assert not ConservationTest(check_charge=False).run(lambda: state).passed


def test_finite_fields_with_overflowing_totals_cannot_pass():
    assert not steady(terminal_currents_A=[1e308, 1e308, -1e308, -1e308]).passed
    check = ConservationTest(check_charge=False)
    assert not check.run(lambda: dict(converged=True,
        energy_initial=[1e308, 1e308], energy_final=[1e308, 1e308])).passed


def test_transient_envelope_failure_overrides_valid_snapshots():
    states = [snapshot(0.0, 0.0), snapshot(1e-9, 1e-18)]
    check = TransientConservationTest()
    assert check.run(lambda: dict(snapshots=states)).passed
    assert not check.run(lambda: dict(converged=False, snapshots=states)).passed


def test_charging_device_conserves_charge_with_nonzero_delta_q():
    # 1 nA for 3 ns adds 3e-18 C; the unbalanced instantaneous terminal
    # currents are exactly the influx that accounts for this stored charge.
    states = [snapshot(0.0, 0.0), snapshot(1e-9, 1e-18), snapshot(3e-9, 3e-18)]
    check = TransientConservationTest()
    assert check.run(lambda: states).passed
    states[-1]["stored_charge_C"] = 4e-18
    assert not check.run(lambda: states).passed


def test_transient_charge_components_are_carried_in_the_total_ledger():
    states = [
        dict(converged=True, time_s=0.0,
             stored_charge_components_C={"mobile": 0.0, "polarization": 0.0,
                                        "trap": 0.0},
             terminal_currents_A=[3e-9, 0.0]),
        dict(converged=True, time_s=1e-9,
             stored_charge_components_C={"mobile": 1e-18, "polarization": 2e-18,
                                        "trap": 0.0},
             terminal_currents_A=[3e-9, 0.0]),
    ]
    result = TransientConservationTest().run(lambda: states)
    assert result.passed
    assert result.details["charge_component_deltas_C"]["polarization"] == [2e-18]
    states[1]["stored_charge_components_C"].pop("trap")
    assert not TransientConservationTest().run(lambda: states).passed


def test_missing_charge_component_snapshot_cannot_hide_a_ledger_channel():
    states = [snapshot(0.0, 0.0), snapshot(1e-9, 1e-18)]
    states[0]["stored_charge_components_C"] = {"mobile": 0.0}
    states[1]["stored_charge_components_C"] = {"mobile": 1e-18, "trap": 0.0}
    assert not TransientConservationTest().run(lambda: states).passed


def test_static_charge_does_not_hide_transient_influx():
    states = [snapshot(0.0, 0.0), snapshot(1e-9, 0.0)]
    assert not TransientConservationTest().run(lambda: states).passed


def test_density_charge_uses_nonuniform_control_volumes():
    states = []
    for t, rho in [(0.0, [0.0, 0.0]), (1e-9, [1.0, 2.0])]:
        states.append(dict(converged=True, time_s=t, charge_density_C_per_m3=rho,
            cell_volumes_m3=[1e-18, 2e-18], terminal_currents_A=[5e-9, 0.0]))
    assert TransientConservationTest().run(lambda: states).passed
    states[-1]["cell_volumes_m3"] = [1e-18, 1e-18]
    assert not TransientConservationTest().run(lambda: states).passed


@pytest.mark.parametrize("change", ["one_snapshot", "missing_time", "same_time",
    "nan_charge", "failed_snapshot", "missing_current", "missing_volume", "wrong_shape"])
def test_incomplete_transient_evidence_cannot_pass(change):
    states = [snapshot(0.0, 0.0), snapshot(1e-9, 1e-18)]
    last = states[-1]
    if change == "one_snapshot":
        states.pop()
    elif change == "missing_time":
        last.pop("time_s")
    elif change == "same_time":
        last["time_s"] = 0.0
    elif change == "nan_charge":
        last["stored_charge_C"] = np.nan
    elif change == "failed_snapshot":
        last["converged"] = False
    elif change == "missing_current":
        last.pop("terminal_currents_A")
    else:
        last.pop("stored_charge_C")
        last["charge_density_C_per_m3"] = [1.0, 2.0]
        if change == "wrong_shape":
            last["cell_volumes_m3"] = [1e-18, 2e-18, 3e-18]
    assert not TransientConservationTest().run(lambda: states).passed


def test_time_quadrature_is_explicit():
    states = [snapshot(0.0, 0.0, (0.0, 0.0)), snapshot(1e-9, 1e-18, (1e-9, 0.0))]
    assert TransientConservationTest(integration="backward_euler").run(lambda: states).passed
    assert not TransientConservationTest(integration="trapezoid").run(lambda: states).passed


def test_public_transient_configuration_protocol():
    class Simulator:
        def set_transient(self, dt, t_final):
            assert dt == 1e-9 and t_final == 1e-7

        def run_transient(self):
            return [snapshot(0.0, 0.0), snapshot(1e-9, 1e-18)]

    assert TransientConservationTest().run(Simulator).passed


def pn_device(bias=0.05):
    from tcad.geometry.device_builder import Device
    from tcad.mesh.generator import structured_mesh_from_device
    from tcad.simulator import Simulator

    device = Device.pnjunction(L=200e-9, W=100e-9, H=100e-9,
        x_junction=100e-9, Na=5e17, Nd=1e18)
    sim = Simulator(structured_mesh_from_device(device, nx=81, ny=1, nz=1))
    sim.set_material_from_mesh()
    sim.set_contact("p_contact", voltage=bias)
    sim.set_contact("n_contact", voltage=0.0)
    return sim


def test_native_doped_pn_kcl_and_absolute_contact_area():
    from tcad.postprocess.current import terminal_currents_1d

    sim = pn_device()
    result = sim.run(max_iter=200, tol=1e-9)
    assert result["converged"]
    currents = terminal_currents_1d(sim, result, cross_section_m2=1e-14)
    wider = terminal_currents_1d(sim, result, cross_section_m2=2e-14)
    assert currents["p_contact"] != 0.0
    assert wider["p_contact"] == pytest.approx(2 * currents["p_contact"])
    assert np.sum(result["n"] - result["p"]) / np.sum(result["n"] + result["p"]) > 0.1
    check = ConservationTest(check_energy=False, current_atol_A=0.0)
    assert check.run(lambda: dict(result, terminal_currents_A=currents)).passed
    broken = dict(currents)
    broken["n_contact"] *= 0.5
    assert not check.run(lambda: dict(result, terminal_currents_A=broken)).passed


@pytest.mark.parametrize("area", [0.0, -1.0, np.nan, np.inf])
def test_contact_area_must_be_explicit_and_physical(area):
    from tcad.postprocess.current import terminal_currents_1d

    with pytest.raises(ValueError, match="cross_section_m2"):
        terminal_currents_1d(SimpleNamespace(), {}, cross_section_m2=area)


def test_line_integration_cannot_silently_accept_3d_mesh():
    from tcad.postprocess.current import terminal_currents_1d

    sim = SimpleNamespace(mesh=SimpleNamespace(ny=2, nz=2))
    with pytest.raises(ValueError, match="ny=nz=1"):
        terminal_currents_1d(sim, {}, cross_section_m2=1e-14)


@pytest.mark.parametrize("masks", [
    {"contact_a": [1, 1, 0], "contact_b": [0, 1, 1]},
    {"contact_a": [0, 1, 0], "contact_b": [0, 0, 1]},
    {"contact_a": [1, 0, 1], "contact_b": [0, 0, 1]},
])
def test_invalid_1d_contact_topology_fails(masks):
    from tcad.postprocess.current import terminal_currents_1d

    sim = SimpleNamespace(mesh=SimpleNamespace(ny=1, nz=1, nx=3, fields=masks))
    with pytest.raises(ValueError, match="contacts"):
        terminal_currents_1d(sim, {}, cross_section_m2=1e-14)
