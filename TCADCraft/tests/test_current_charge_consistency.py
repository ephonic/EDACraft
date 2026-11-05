"""Loaded-solver charge versus standalone SI transport, with independent currents."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tcad.core import native_constants
from tcad.mesh.structured_grid import StructuredGrid
from tcad.simulator import Simulator
from tcad.postprocess.current import (
    QE, sg_current_density_1d, sg_current_density_1d_z,
    contact_current_1d, contact_current_2d, terminal_currents_1d,
)
from tcad.postprocess.trust import kcl_residual_1d


def compiled_charge():
    return {'si': 1.602176634e-19, 'legacy-charge': 1.602192e-19}[native_constants()['profile']]


def problem(geometry, layout=0):
    axis = 2 if geometry == 'slab_z' else 0
    coords = np.array([0., .1, .4, .7, 1.] if layout == 0 else
                      [0., .01, .04, .5, .95, 1.]) * .6e-6
    axes = [np.array([0.])] * 3
    axes[axis] = coords
    if geometry != 'line':
        axes[2 if axis == 0 else 0] = np.array([0., .05, .2, .4])*1e-6
    bbox = [(0., 1e-6)]*3
    bbox[axis] = (0., .6e-6)
    if geometry != 'line':
        bbox[2 if axis == 0 else 0] = (0., .4e-6)
    mesh = StructuredGrid(tuple(bbox), *(len(a) for a in axes), axes=axes)
    xx = mesh.flat_coords()[axis]
    mesh.fields.update(mu_n=np.full(mesh.npts(), .1), mu_p=np.full(mesh.npts(), .05),
                       contact_low=xx == 0., contact_high=xx == coords[-1])
    return Simulator(mesh), xx, axis


def terminals(sim, state, geometry):
    if geometry == 'line':
        values = terminal_currents_1d(sim, state, cross_section_m2=.4e-6*1e-6)
        return [values['low'], values['high']]
    return [contact_current_2d(sim, state, name) for name in ['low', 'high']]


def solved_record(geometry, layout, bias):
    # Neutral affine resistor solves Poisson and both continuity equations.
    sim, xx, axis = problem(geometry, layout)
    mesh = sim.mesh; size = mesh.npts(); low = sim._sim; density = 1e16
    low.set_mobility(mesh.fields['mu_n'], mesh.fields['mu_p'])
    low.set_effective_dos(np.full(size, density), np.full(size, density))
    low.set_bandgap(np.zeros(size))
    low.set_recombination(np.full(size, 1e100), np.full(size, 1e100))
    contacts = np.flatnonzero(mesh.fields['contact_low'] | mesh.fields['contact_high'])
    potential = bias*(1-xx/.6e-6)
    low.set_dirichlet_potential({int(i): float(potential[i]) for i in contacts})
    low.set_electron_bc({int(i): density for i in contacts})
    low.set_hole_bc({int(i): density for i in contacts})
    low.set_initial_guess(potential, np.full(size, density), np.full(size, density))
    low.set_use_newton(False)
    state = sim.run(max_iter=80, tol=1e-12, physical_step=False)
    old_state = {key: state[key] for key in ['phi', 'n', 'p']}
    current = {source: terminals(sim, fields, geometry) for source, fields in
               [('native', state), ('fallback', old_state)]}
    # Exported amperes must not be charge-scaled a second time.
    leakage = 3.125
    state_with_leak = dict(state, **{'Jleak_'+'xyz'[axis]: np.full(size, leakage)})
    old_with_leak = dict(old_state, **{'Jleak_'+'xyz'[axis]: np.full(size, leakage)})
    with_leak = {source: terminals(sim, fields, geometry) for source, fields in
                 [('native', state_with_leak), ('fallback', old_with_leak)]}
    q = compiled_charge(); area = .4e-6*1e-6
    expected_n = q*.1*density*bias/.6e-6*area
    expected_p = q*.05*density*bias/.6e-6*area
    return dict(geometry=geometry, layout=layout, bias_V=bias, converged=bool(state['converged']),
                simulator_charge_C=getattr(sim, 'elementary_charge_C', None),
                profile=native_constants()['profile'], expected_n_A=expected_n,
                expected_p_A=expected_p, currents_A=current, with_leak_A=with_leak,
                added_leak_A=leakage*area, kcl=(kcl_residual_1d(sim, old_state)
                                               if axis == 0 else None))


@pytest.mark.parametrize('geometry', ['line', 'slab_x', 'slab_z'])
@pytest.mark.parametrize('layout', [0, 1])
@pytest.mark.parametrize('bias', [.01, -.01])
def test_solved_native_fallback_charge_and_unscaled_leakage(geometry, layout, bias):
    record = solved_record(geometry, layout, bias)
    assert record['converged']
    assert record['simulator_charge_C'] == compiled_charge()
    expected = record['expected_n_A'] + record['expected_p_A']
    for values in record['currents_A'].values():
        np.testing.assert_allclose(values, [expected, -expected], rtol=2e-10, atol=0.)
    for values in record['with_leak_A'].values():
        total = expected + record['added_leak_A']
        np.testing.assert_allclose(values, [total, -total], rtol=2e-10, atol=0.)
    if record['kcl'] is not None:
        assert record['kcl'] < 1e-10


def test_simulator_charge_is_readonly_and_follows_binary_not_environment(monkeypatch):
    sim, _, _ = problem('line')
    expected = compiled_charge()
    assert sim.elementary_charge_C == expected
    for profile in ['si', 'legacy-charge', 'invalid']:
        monkeypatch.setenv('TCAD_CONSTANTS_PROFILE', profile)
        assert sim.elementary_charge_C == expected
        assert problem('line')[0].elementary_charge_C == expected
    with pytest.raises(AttributeError):
        sim.elementary_charge_C = 1.
    assert sim.configuration_snapshot() == []


@pytest.mark.parametrize('geometry', ['line', 'slab_x', 'slab_z'])
@pytest.mark.parametrize('mode', ['drift', 'diffusion'])
@pytest.mark.parametrize('carrier', ['n', 'p', 'both'])
def test_manufactured_carrier_limits_use_solver_charge(geometry, mode, carrier):
    sim, xx, axis = problem(geometry)
    size = sim.mesh.npts(); q = compiled_charge()
    n = np.full(size, 1e20) if carrier in ['n', 'both'] else np.zeros(size)
    p = np.full(size, 2e20) if carrier in ['p', 'both'] else np.zeros(size)
    if mode == 'drift':
        phi = xx*1e4
        jn = -q*.1*n[0]*1e4; jp = -q*.05*p[0]*1e4
    else:
        phi = np.zeros(size)
        if carrier in ['n', 'both']: n += 1e26*xx
        if carrier in ['p', 'both']: p += 2e25*xx
        jn = q*.1*sim.VT*1e26 if carrier in ['n', 'both'] else 0.
        jp = -q*.05*sim.VT*2e25 if carrier in ['p', 'both'] else 0.
    fallback = dict(phi=phi, n=n, p=p, **{'Jleak_'+'xyz'[axis]: np.full(size, 3.125)})
    native = dict(fallback, **{'Jn_'+'xyz'[axis]: np.full(size, jn),
                                'Jp_'+'xyz'[axis]: np.full(size, jp)})
    expected = (jn+jp+3.125)*.4e-6*1e-6
    for fields in [fallback, native]:
        np.testing.assert_allclose(terminals(sim, fields, geometry), [expected, -expected],
                                   rtol=3e-14, atol=0.)
    # An independent facade that has no native charge metadata retains SI.
    facade = SimpleNamespace(mesh=sim.mesh, VT=sim.VT)
    expected_si = ((jn+jp)*QE/q+3.125)*.4e-6*1e-6
    np.testing.assert_allclose(terminals(facade, fallback, geometry), [expected_si, -expected_si],
                               rtol=3e-14, atol=0.)


@pytest.mark.parametrize('fun', [sg_current_density_1d, sg_current_density_1d_z])
@pytest.mark.parametrize('mode', ['drift', 'diffusion'])
@pytest.mark.parametrize('charge', [1.602176634e-19, 1.602192e-19, 2.4e-19])
def test_standalone_si_default_and_explicit_charge(fun, mode, charge):
    x = np.array([0., .1, .4, 1.])*1e-6
    phi = 1e4*x if mode == 'drift' else np.zeros(4)
    n = np.full(4, 1e20) if mode == 'drift' else 1e20+1e26*x
    p = np.full(4, 2e20) if mode == 'drift' else 2e20+2e25*x
    expected = [-.1*1e20*1e4, -.05*2e20*1e4] if mode == 'drift' else [.1*.02585*1e26, -.05*.02585*2e25]
    args = (phi, n, p, np.diff(x), np.full(4, .1), np.full(4, .05), .02585)
    for actual, reference in zip(fun(*args), expected):
        np.testing.assert_allclose(actual, QE*reference, rtol=3e-14)
    for actual, reference in zip(fun(*args, elementary_charge_C=charge), expected):
        np.testing.assert_allclose(actual, charge*reference, rtol=3e-14)


@pytest.mark.parametrize('charge', [0., -1., np.nan, np.inf, -np.inf, True,
                                  [1e-19], [[1e-19]], '1e-19', 1e-19+0j, None])
@pytest.mark.parametrize('fun', [sg_current_density_1d, sg_current_density_1d_z])
def test_invalid_explicit_charge_rejected_without_mutation(fun, charge):
    arrays = [np.array([0., .01, .02]), np.ones(3)*1e20, np.ones(3)*2e20,
              np.ones(3)*.1, np.ones(3)*.05]
    before = [v.copy() for v in arrays]
    with pytest.raises(ValueError, match='elementary_charge_C'):
        fun(*arrays[:3], 1e-7, *arrays[3:], .02585, elementary_charge_C=charge)
    for actual, old in zip(arrays, before):
        np.testing.assert_array_equal(actual, old)


def test_exported_native_fluxes_are_used_without_reading_charge():
    sim, _, _ = problem('line')
    facade = SimpleNamespace(mesh=sim.mesh, VT=sim.VT, elementary_charge_C=np.nan)
    size = sim.mesh.npts()
    state = dict(Jn_x=np.full(size, 1.), Jp_x=np.full(size, 2.), Jleak_x=np.full(size, 3.))
    assert contact_current_1d(facade, state, 'low') == 6.
    assert contact_current_1d(facade, state, 'high') == -6.
    assert kcl_residual_1d(facade, state) == 0.


if __name__ == '__main__':
    records = [solved_record(g, layout, bias) for g in ['line', 'slab_x', 'slab_z']
               for layout in [0, 1] for bias in [.01, -.01]]
    Path(sys.argv[1]).write_text(json.dumps(dict(constants=native_constants(), records=records), indent=2))
