"""Independent-temperature FD transport, conservative exchange and device first law."""
from copy import deepcopy
import numpy as np
import pytest
from scipy.optimize import root

from tcad.solver.three_temperature import ThreeTemperatureElectrothermal, ThreeTemperatureState
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy
from tcad.postprocess.fermi_spectral_energy import reference_reservoir
from test_fermi_spectral import fixture, BUDGET


def case(*, contacts=False, voltage=0., count=2, density_scale=1., uniform=False, reverse=False, nonuniform=False):
    old_model, old = fixture(contacts=contacts, voltage=voltage, count=count,
                             density_scale=density_scale, reverse=reverse)
    mesh = old_model.mesh
    conductivity = old_model.conductivity
    if nonuniform:
        from tcad.mesh.polyhedral_regions import region_cut_cells
        mesh = region_cut_cells([np.array([0.,1.5e-8,1e-7]),np.array([0.,1e-7]),np.array([0.,1e-7])],{'box':[[]]})
        conductivity = np.array([.001,.004])
    model = ThreeTemperatureElectrothermal(mesh, permittivity_F_m=old_model.eps,
        dirichlet_V=old_model.bc, mobility_n_m2_Vs=old_model.mn, mobility_p_m2_Vs=old_model.mp,
        Ec_J=0. if uniform else old_model.Ec, Eh_J=0. if uniform else old_model.Eh,
        heat_capacity_J_m3_K=old_model.capacity, thermal_conductivity_W_m_K=conductivity,
        valleys_n=old_model.valleys['electrons'], valleys_p=old_model.valleys['holes'],
        thermionic_faces=old_model.thermionic_faces, particle_contacts=old_model.contacts,
        heat_bath_K=old_model.bath, terminal_groups=old_model.groups,
        relaxation_time_n_s=1e-13, relaxation_time_p_s=4e-13)
    density = np.full(count, 1e25*density_scale) if uniform else old.n_m3
    Tl = np.full(count, 300.) if uniform else old.temperature_K
    return model, ThreeTemperatureState(density, density, old.trap_fraction, Tl, 0., Tl+60., Tl-40.)


@pytest.mark.parametrize('contacts,voltage,count,scale', [
    (False,0.,2,1.), (False,0.,2,10.), (True,0.,2,1.), (True,.002,2,1.),
    (True,-.002,2,1.), (True,.002,4,1.), (True,.002,2,10.), (True,-.002,2,10.)])
def test_two_actual_steps_advance_independent_temperatures_and_close_energy(contacts, voltage, count, scale):
    model, state = case(contacts=contacts, voltage=voltage, count=count, density_scale=scale)
    before = state
    for _ in range(2):
        old = state
        state, report = model.step(old, 2e-13, **BUDGET)
        assert report['independent_audit']['valid'] and report['modeled_device_energy_closed']
        assert report['complete_device_energy'] is False and report['physical_validated'] is False
        assert audit_three_temperature_energy(model, old, state, report, **BUDGET)['valid']
        assert max(abs(state.electron_temperature_K-state.temperature_K)) > .1
        assert max(abs(state.hole_temperature_K-state.temperature_K)) > .1
        assert state.time_s > old.time_s
        assert not state.electron_temperature_K.flags.writeable
    assert max(abs(state.electron_temperature_K-before.electron_temperature_K)) > 1.


def test_uniform_closed_relaxation_matches_independent_FD_three_reservoir_root():
    model, old = case(count=1, uniform=True)
    new, report = model.step(old, 2e-13, **BUDGET)
    density = old.n_m3[0]
    def U(T, label):
        return reference_reservoir(density, T, 0., model.valleys[label])['energy_density_J_m3']
    un, up = U(360., 'electrons'), U(260., 'holes')
    def residual(T):
        Tn, Tp, Tl = T
        rn = (U(Tn,'electrons')-U(Tl,'electrons'))*2e-13/model.tau_n[0]
        rp = (U(Tp,'holes')-U(Tl,'holes'))*2e-13/model.tau_p[0]
        return [U(Tn,'electrons')-un+rn, U(Tp,'holes')-up+rp,
                model.capacity[0]*(Tl-300.)-rn-rp]
    solution = root(residual, [320.,280.,300.], tol=1e-10)
    assert solution.success
    np.testing.assert_allclose([new.electron_temperature_K[0],new.hole_temperature_K[0],new.temperature_K[0]],
                               solution.x, rtol=0., atol=2e-6)
    assert report['cell_exchange_J']['electrons'][0] > 0
    assert report['cell_exchange_J']['holes'][0] < 0
    assert abs(report['energy_residual_J']) <= BUDGET['energy_atol_J']
    np.testing.assert_array_equal(new.n_m3, old.n_m3)


@pytest.mark.parametrize('damage', ['electron_storage','hole_storage','lattice_storage','exchange_n',
    'exchange_p','electron_flux','hole_flux','heat_flux','local','terminal','work','scope','closed_claim'])
def test_independent_audit_rejects_corrupted_energy_components(damage):
    model, old = case(contacts=True, voltage=.002)
    new, report = model.step(old, 2e-13, **BUDGET)
    bad = deepcopy(report)
    if damage.endswith('_storage'):
        bad['energy_increments_J'][damage.split('_')[0]+'s' if damage.startswith(('electron','hole')) else 'lattice'] += 1e-20
    elif damage.startswith('exchange_'):
        bad['cell_exchange_J']['electrons' if damage.endswith('n') else 'holes'][0] += 1e-20
    elif damage in ('electron_flux','hole_flux'):
        bad['integrated_carrier_energy_flux_W']['electrons' if damage.startswith('electron') else 'holes'][0] += 1e-8
    elif damage == 'heat_flux':bad['integrated_heat_flux_W'][0] += 1e-8
    elif damage == 'local':bad['cell_energy_residuals_J'][0] += 1e-20
    elif damage == 'terminal':bad['terminal_currents_A'][next(iter(model.bc))] += 1e-8
    elif damage == 'work':bad['source_work_J'] += 1e-20
    elif damage == 'scope':bad['scope'] = 'complete_device'
    else:bad['complete_device_energy'] = True
    assert not audit_three_temperature_energy(model, old, new, bad, **BUDGET)['valid']


def test_failed_step_does_not_mutate_input_and_retry_matches_fresh():
    model, old = case(contacts=True, voltage=.002)
    fields = ('n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K')
    saved = [getattr(old,k).tobytes() for k in fields]
    with pytest.raises(RuntimeError, match='budget'):
        model.step(old, 2e-13, max_nfev=1, **BUDGET)
    assert saved == [getattr(old,k).tobytes() for k in fields] and old.time_s == 0.
    retry, _ = model.step(old, 2e-13, **BUDGET)
    fresh, _ = case(contacts=True, voltage=.002)
    expected, _ = fresh.step(old, 2e-13, **BUDGET)
    for k in fields:np.testing.assert_array_equal(getattr(retry,k), getattr(expected,k))


def test_audit_calls_no_production_physics(monkeypatch):
    model, old = case(contacts=True, voltage=.002)
    new, report = model.step(old, 2e-13, **BUDGET)
    def forbidden(*args, **kwargs):raise AssertionError('production physics used by audit')
    for name in ('_poisson','carrier_reservoirs','split_face_transport','conduction','energies'):
        monkeypatch.setattr(model, name, forbidden)
    assert audit_three_temperature_energy(model, old, new, report, **BUDGET)['valid']


@pytest.mark.parametrize('bad', [0., -1e-13, float('nan'), float('inf'), True, 1j])
def test_invalid_relaxation_rejected(bad):
    model, old = case()
    model.tau_n = bad
    with pytest.raises(ValueError):model.step(old, 2e-13, **BUDGET)


@pytest.mark.parametrize('bad', [None, [0.,300.], [300+1j,300], ['300','300'], [300.]])
def test_independent_temperature_state_requires_explicit_real_positive_arrays(bad):
    model, old = case()
    with pytest.raises(ValueError):
        ThreeTemperatureState(old.n_m3,old.p_m3,old.trap_fraction,old.temperature_K,0.,bad,old.hole_temperature_K)


def test_shared_temperature_apis_do_not_silently_drop_independent_temperatures():
    model, old = case()
    with pytest.raises(ValueError,match='explicit'):model.face_transport(old.n_m3,old.p_m3,old.temperature_K,{})
    with pytest.raises(ValueError,match='independent'):model.carrier_density_energy(old.n_m3,old.p_m3,old.temperature_K)
    values, _ = model.energies(old, charge_atol_C=2e-28)
    assert set(values) == {'electrons','holes','lattice','electrostatic'}


def test_graded_mesh_conduction_uses_individual_half_cell_thermal_resistances():
    model, old = case(nonuniform=True)
    heat = model.conduction(np.array([400.,300.]))
    f = int(model.internal[0]); face = model.mesh.faces[f]
    area = np.linalg.norm(face.area_vector_m2)
    do = np.linalg.norm(face.centroid_m-model.mesh.centroids_m[face.owner])
    dn = np.linalg.norm(face.centroid_m-model.mesh.centroids_m[face.neighbor])
    expected = area/(do/.001+dn/.004)*100.
    assert heat[f] == pytest.approx(expected,rel=1e-14)
    unweighted = 2*.001*.004/(.001+.004)*area/(do+dn)*100.
    assert abs(heat[f]/unweighted-1) > .1
    new, report = model.step(old,2e-13,**BUDGET)
    assert audit_three_temperature_energy(model,old,new,report,**BUDGET)['valid']


@pytest.mark.parametrize('field', ['n_m3','p_m3','temperature_K','trap_fraction'])
def test_complex_state_arrays_are_not_silently_rounded(field):
    model, old = case()
    data={k:getattr(old,k) for k in ('n_m3','p_m3','trap_fraction','temperature_K','time_s',
        'electron_temperature_K','hole_temperature_K')}
    data[field]=np.asarray(data[field],dtype=complex)+1j
    with pytest.raises(ValueError,match='real'):ThreeTemperatureState(**data)


@pytest.mark.parametrize('field', ['valid','state_advanced'])
def test_audit_does_not_accept_false_success_metadata(field):
    model,old=case(uniform=True,count=1)
    new,report=model.step(old,2e-13,**BUDGET)
    report[field]=False
    assert not audit_three_temperature_energy(model,old,new,report,**BUDGET)['valid']
