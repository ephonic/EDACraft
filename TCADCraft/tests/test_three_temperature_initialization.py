"""Fixed-lattice preparation, independent stationary rows and failed-seed isolation."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest

from tcad.mesh.polyhedral_regions import region_cut_cells
from tcad.physics.multivalley_thermionic import ThermionicValley
from tcad.solver.cut_cell_transport import Q
from tcad.solver.electrothermal_cut_cell import CarrierReservoir
from tcad.solver.three_temperature import ThreeTemperatureElectrothermal, ThreeTemperatureState
from tcad.solver.three_temperature_initialization import prepare_lattice_clamped_state
from tcad.postprocess.three_temperature_initialization import audit_lattice_clamped_state

BUDGET = dict(charge_atol_C=2e-28, particle_flux_atol_s=1e4,
              energy_power_atol_W=1e-16, current_atol_A=1e-15)


def case(count=2, voltage=.002, path='linear_series', density=1e22, coupled=False):
    length = 1e-7
    mesh = region_cut_cells([np.linspace(0, length, count+1), np.array([0., length]),
                            np.array([0., length])], {'box': [[]]})
    groups = {side: [f for f, face in enumerate(mesh.faces) if face.neighbor < 0
        and abs(face.area_vector_m2[0]) > 0 and (face.centroid_m[0] < length/2) == (side == 'left')]
        for side in ('left', 'right')}
    bc = {f: 0. if side == 'left' else voltage for side, faces in groups.items() for f in faces}
    contacts = {f: CarrierReservoir(density*(2 if side == 'left' else 1),
        density*(1 if side == 'left' else 2), 300.) for side, faces in groups.items() for f in faces}
    x = mesh.centroids_m[:, 0]/length; n = density*(2-x); p = density*(1+x)
    model = ThreeTemperatureElectrothermal(mesh, permittivity_F_m=1e-10, dirichlet_V=bc,
        fixed_charge_C_m3=Q*(n-p), mobility_n_m2_Vs=.01, mobility_p_m2_Vs=.006,
        Ec_J=.02*Q, Eh_J=.04*Q, valleys_n=(ThermionicValley('e', 1, .5, .5, .5),),
        valleys_p=(ThermionicValley('h', 1, .6, .6, .6),), particle_contacts=contacts,
        terminal_groups=groups, heat_bath_K={f: 300. for f in bc}, heat_capacity_J_m3_K=1e3,
        thermal_conductivity_W_m_K=1e-4, relaxation_time_n_s=1e-13, relaxation_time_p_s=2e-13,
        intercarrier_conductance_W_m3_K=1e8 if coupled else 0., bulk_potential_path=path)
    initial = ThreeTemperatureState(n, p, np.full(count, .3), 310.+20*x, 7e-12,
                                    350.+10*x, 290.+10*x)
    return model, initial


@pytest.mark.parametrize('count,voltage,path,density,coupled', [
    (1, .002, 'linear_series', 1e22, False),
    (2, -.002, 'linear_series', 1e22, True),
    (3, .002, 'endpoint_barrier', 1e22, False),
    (2, .002, 'linear_series', 1e25, False)])
def test_prepares_four_stationary_rows_and_reports_external_clamp(count, voltage, path, density, coupled, monkeypatch):
    model, initial = case(count, voltage, path, density, coupled)
    saved = initial.n_m3.tobytes(); configuration = model.rhofix.tobytes()
    prepared, report = prepare_lattice_clamped_state(model, initial, **BUDGET)
    assert report['independent_audit']['valid']
    assert prepared.time_s == initial.time_s and not report['clock_advanced']
    np.testing.assert_array_equal(prepared.temperature_K, initial.temperature_K)
    assert initial.n_m3.tobytes() == saved and model.rhofix.tobytes() == configuration
    assert not prepared.n_m3.flags.writeable
    assert 1 < report['residual_evaluations'] <= report['max_nfev']
    assert report['residual_evaluations'] == int(report['nonlinear_statistics'][0])
    assert np.max(abs(report['integrated_particle_flux_s']['electrons'])) > BUDGET['particle_flux_atol_s']
    assert np.max(abs(report['cell_clamp_heat_input_W'])) > BUDGET['energy_power_atol_W']
    assert not report['complete_device_energy'] and not report['lattice_energy_equation_solved']
    assert np.max(abs(prepared.electron_temperature_K-initial.electron_temperature_K)) > 1.
    import tcad.core as public
    import tcad.core._bindings as native
    def forbidden(*args, **kwargs):
        raise AssertionError('native production physics in independent preparation audit')
    for module in (public, native):
        for name in dir(module):
            if (name.startswith('native_') or name.startswith('three_temperature_')) and callable(getattr(module, name)):
                monkeypatch.setattr(module, name, forbidden)
    for name in ('_poisson', 'split_face_transport', 'carrier_reservoirs', 'relaxation_times', 'conduction'):
        monkeypatch.setattr(model, name, forbidden)
    assert audit_lattice_clamped_state(model, initial, prepared, report, **BUDGET)['valid']


def test_budget_failure_and_native_exception_leave_seed_unchanged(monkeypatch):
    model, initial = case(); original = deepcopy(initial)
    with pytest.raises(RuntimeError, match='budget'):
        prepare_lattice_clamped_state(model, initial, max_nfev=1, **BUDGET)
    import tcad.core._bindings as native
    with monkeypatch.context() as patch:
        def fail(*args, **kwargs):
            raise RuntimeError('forced preparation failure')
        patch.setattr(native, 'native_fermi_newton_raw', fail)
        with pytest.raises(RuntimeError, match='forced'):
            prepare_lattice_clamped_state(model, initial, **BUDGET)
    for name in ('n_m3', 'p_m3', 'trap_fraction', 'temperature_K', 'electron_temperature_K', 'hole_temperature_K'):
        np.testing.assert_array_equal(getattr(initial, name), getattr(original, name))
    prepared, report = prepare_lattice_clamped_state(model, initial, **BUDGET)
    assert report['independent_audit']['valid'] and prepared.time_s == original.time_s


@pytest.mark.parametrize('damage', ['particle', 'energy', 'clamp', 'potential', 'complete', 'lattice_claim',
                                    'extra_channel', 'clock', 'lattice'])
def test_independent_preparation_audit_rejects_corruption(damage):
    model, initial = case(count=1)
    prepared, report = prepare_lattice_clamped_state(model, initial, **BUDGET)
    bad = deepcopy(report)
    if damage == 'particle': bad['integrated_particle_flux_s']['electrons'][0] += 1e8
    elif damage == 'energy': bad['integrated_carrier_energy_flux_W']['holes'][0] += 1e-8
    elif damage == 'clamp': bad['cell_clamp_heat_input_W'][0] += 1e-8
    elif damage == 'potential': bad['poisson']['cell_potential_V'][0] += .001
    elif damage == 'complete': bad['complete_device_energy'] = True
    elif damage == 'lattice_claim': bad['lattice_energy_equation_solved'] = True
    elif damage == 'extra_channel': bad['cell_carrier_energy_residual_W']['photons'] = np.zeros(1)
    elif damage == 'clock': prepared = replace(prepared, time_s=prepared.time_s+1e-12)
    else: prepared = replace(prepared, temperature_K=prepared.temperature_K+1.)
    assert not audit_lattice_clamped_state(model, initial, prepared, bad, **BUDGET)['valid']


@pytest.mark.parametrize('configuration', ['no_contact', 'blocked_component', 'generation', 'radiative', 'bands'])
def test_unsupported_source_or_unanchored_component_rejected(configuration):
    model, initial = case()
    if configuration == 'no_contact': model.contact_faces = np.array([], int)
    elif configuration == 'blocked_component':
        # A blocked internal face and one removed reservoir leave one component unanchored.
        face = int(model.internal[0]); model.emission['electrons'][face] = 0.
        model.contact_faces = np.array([model.contact_faces[0]], int)
    elif configuration == 'generation': model.pair_generation_rate_m3_s = np.ones(2)*1e25
    elif configuration == 'radiative': model.radiative_law = 'matched_direct_gap_FD_Planck'
    else: model.band_temperature_slopes = (np.ones(2)*1e-23, np.zeros(2))
    with pytest.raises(ValueError):
        prepare_lattice_clamped_state(model, initial, **BUDGET)


@pytest.mark.parametrize('budget', [0, -1, True, 1.5])
def test_invalid_iteration_budget_rejected(budget):
    model, initial = case()
    with pytest.raises(ValueError):
        prepare_lattice_clamped_state(model, initial, max_nfev=budget, **BUDGET)
