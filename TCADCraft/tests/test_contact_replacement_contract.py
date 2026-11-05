"""Contact replacement and rejection must preserve the requested reservoirs."""
from copy import deepcopy
import json

import numpy as np
import pytest

from tcad.core import native_constants
from tcad.mesh.structured_grid import StructuredGrid
from tcad.postprocess import terminal_currents_native
from tcad.simulator import Simulator


class Capture:
    def __init__(self, backend):
        self.backend, self.calls = backend, []

    def __getattr__(self, name):
        method = getattr(self.backend, name)
        if not callable(method):
            return method

        def call(*args, **kwargs):
            self.calls.append((name, deepcopy(args), deepcopy(kwargs)))
            return method(*args, **kwargs)
        return call


def make_sim(axis=0, graded=False, count=7):
    spans = (1e-6, 2e-7, 3e-7)
    shape = tuple(count if a == axis else 1 for a in range(3))
    axes = [span*np.linspace(0., 1., size)**(1.3 if graded else 1.)
            for span, size in zip(spans, shape)]
    mesh = StructuredGrid(tuple((0., span) for span in spans), *shape, axes=axes)
    size = mesh.npts()
    mesh.fields.update(doping=np.zeros(size), Nc=np.full(size, 1e10),
        Nv=np.full(size, 1e10), Eg=np.zeros(size), chi=np.full(size, 4.05),
        epsilon=np.full(size, 11.7*8.854187817e-12),
        mu_n=np.full(size, .1), mu_p=np.full(size, .05),
        contact_left=np.arange(size) == 0, contact_right=np.arange(size) == size-1)
    sim = Simulator(mesh)
    sim.set_material_from_mesh()
    sim.set_quantum(False)
    sim._sim.set_recombination(np.full(size, 1e100), np.full(size, 1e100))
    return sim


def observe_valid_contact(sim):
    sim.set_contact('left', .012, 4.2)
    observer = Capture(sim._sim)
    sim._sim = observer
    before = deepcopy((sim._contact_voltages, sim._contact_workfunctions))
    recipe = sim.configuration_snapshot()
    return observer, before, recipe


def assert_rejection_preserved(sim, observer, before, recipe):
    assert observer.calls == []
    assert (sim._contact_voltages, sim._contact_workfunctions) == before
    # The failed operation must not enter the replay recipe. Arrays need an
    # explicit comparison, rather than ambiguous dictionary equality.
    after = sim.configuration_snapshot()
    assert repr(after) == repr(recipe)


BAD_SCALARS = [np.nan, np.inf, -np.inf, 0.1+0j, [.1], np.array([.1]), '0.1', True]


@pytest.mark.parametrize('value', BAD_SCALARS)
@pytest.mark.parametrize('argument', ['voltage', 'workfunction'])
def test_invalid_scalar_never_reaches_native_boundary(argument, value):
    sim = make_sim()
    observer, before, recipe = observe_valid_contact(sim)
    kwargs = dict(voltage=.02, workfunction=4.3)
    kwargs[argument] = value
    with pytest.raises(ValueError, match='finite real scalar'):
        sim.set_contact('left', **kwargs)
    assert_rejection_preserved(sim, observer, before, recipe)


@pytest.mark.parametrize('bad', ['nan', 'inf', 'negative', 'fraction', 'complex',
                               'short', 'long', 'string', 'empty'])
@pytest.mark.parametrize('wrap_gate', [False, True])
def test_invalid_contact_mask_never_changes_a_boundary(bad, wrap_gate):
    sim = make_sim()
    size = sim.mesh.npts()
    values = np.zeros(size)
    values[0] = 1.
    if bad in ('nan', 'inf', 'negative', 'fraction'):
        values[2] = dict(nan=np.nan, inf=np.inf, negative=-1., fraction=.5)[bad]
    elif bad == 'complex':
        values = values.astype(complex)
    elif bad == 'short':
        values = np.ones(1)
    elif bad == 'long':
        values = np.ones(size+1)
    elif bad == 'string':
        values = values.astype(str)
    else:
        values = np.array([])
    name = 'gate' if wrap_gate else 'left'
    if wrap_gate:
        sim.mesh.fields['contact_gate'] = sim.mesh.fields['contact_left'].copy()
        sim.mesh.fields['contact_gate_r'] = values
    else:
        sim.mesh.fields['contact_left'] = values
    # Observe the tested simulator, after a valid pre-existing configuration.
    sim.set_contact('right', -.003)
    observer = Capture(sim._sim)
    sim._sim = observer
    before = deepcopy((sim._contact_voltages, sim._contact_workfunctions))
    recipe = sim.configuration_snapshot()
    with pytest.raises(ValueError, match='binary value per mesh node'):
        sim.set_contact(name, .02)
    assert_rejection_preserved(sim, observer, before, recipe)


@pytest.mark.parametrize('field,value', [('Nc', 0.), ('Nv', 0.), ('Eg', np.nan),
                                        ('chi', np.nan), ('chi', np.inf)])
def test_nonfinite_or_zero_computed_schottky_boundary_is_not_installed(field, value):
    sim = make_sim()
    observer, before, recipe = observe_valid_contact(sim)
    sim.mesh.fields[field][0] = value
    with np.errstate(all='ignore'):
        with pytest.raises(ValueError, match='boundary values'):
            sim.set_contact('left', .02, 4.3)
    assert_rejection_preserved(sim, observer, before, recipe)


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('refine', [False, True])
def test_contact_mode_replacement_survives_configuration_replay(axis, refine):
    sim = make_sim(axis)
    sim.set_contact('left', .012, 4.2)
    sim.set_contact('right', -.003, 4.1)
    sim.set_contact('left', .012)  # an omitted workfunction selects Ohmic
    sim.set_contact('right', -.003, workfunction=None)
    target = make_sim(axis, count=13 if refine else 7).mesh
    clone = sim.clone_on_mesh(target, include_initial_guess=False)
    assert sim._contact_workfunctions == clone._contact_workfunctions == {}
    assert clone._contact_voltages == sim._contact_voltages
    # Re-entering Schottky mode is still possible, and contact modes are local.
    clone.set_contact('left', .012, np.float64(4.4))
    assert clone._contact_workfunctions == {'left': 4.4}
    clone.set_contact('left', .012, None)
    assert clone._contact_workfunctions == {} and sim._contact_workfunctions == {}


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('graded', [False, True])
@pytest.mark.parametrize('newton', [False, True])
def test_replaced_contact_remains_ohmic_across_runs_and_voltage_update(axis, graded, newton):
    sim = make_sim(axis, graded)
    sim.set_use_newton(newton)
    sim._sim.set_newton_primary(newton)
    sim.set_newton_log_space(newton)
    sim.set_contact('left', .012, 4.2)
    sim.set_contact('right', -.003, 4.1)
    sim.set_contact('left', .012)
    sim.set_contact('right', -.003, None)
    spans = (1e-6, 2e-7, 3e-7)
    area = np.prod([span for a, span in enumerate(spans) if a != axis])
    coords = sim.mesh.axis_coordinates()[axis]
    q = float(native_constants()['elementary_charge_C'])
    errors = []
    for step, left in enumerate([.012, .012, .018]):
        if step == 2:
            sim.update_contact('left', left)
        result = sim.run(max_iter=100, tol=1e-10, physical_step=False)
        assert result['converged'] and result['valid'] and result['target_reached']
        assert result['continuation_retries'] == 0
        phi = left - (left+.003)*(coords-coords[0])/(coords[-1]-coords[0])
        np.testing.assert_allclose(result['phi'], phi, rtol=2e-8, atol=2e-10)
        np.testing.assert_allclose(result['n'], 1e16, rtol=2e-7)
        np.testing.assert_allclose(result['p'], 1e16, rtol=2e-7)
        currents = terminal_currents_native(sim, result)
        expected = q*.15*1e16*(left+.003)/spans[axis]*area
        error = max(abs(currents['left']/expected-1), abs(currents['right']/expected+1))
        assert error < 3e-7
        errors.append(error)
    assert sim._contact_workfunctions == {}
    print(json.dumps(dict(contact_replacement=True, profile=native_constants()['profile'],
        axis=axis, graded=graded, newton=newton, native_solves=3,
        user_initial_guess=False, maximum_current_error=max(errors))))


@pytest.mark.parametrize('mask_dtype', [bool, np.int64, np.float64])
def test_valid_binary_masks_and_real_numpy_scalars_keep_schottky_mode(mask_dtype):
    sim = make_sim()
    sim.mesh.fields['contact_left'] = sim.mesh.fields['contact_left'].astype(mask_dtype)
    sim.set_contact('left', np.float64(.02), np.float64(4.3))
    assert sim._contact_workfunctions == {'left': 4.3}
    assert sim._contact_voltages == {'left': .02}
