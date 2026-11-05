"""Ohmic reservoirs against independent charge-neutral Boltzmann solutions."""
from copy import deepcopy
from decimal import Decimal, localcontext
import json

import numpy as np
import pytest

from tcad.core import native_constants
from tcad.mesh.structured_grid import StructuredGrid
from tcad.postprocess import terminal_currents_native
from tcad.simulator import Simulator
from tcad.validation.conservation import ConservationTest


class Capture:
    """Observe calls while forwarding every operation to the real backend."""
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


def equilibrium(doping, nc, nv, gap, vt):
    # High-precision direct quadratic roots are independent of the production
    # hypot/majority-root/mass-action algorithm.  100 digits retain both roots.
    with localcontext() as ctx:
        ctx.prec = 100
        c, nc, nv, gap, vt = map(lambda x: Decimal(str(float(x))),
                                 (doping, nc, nv, gap, vt))
        ni = (nc * nv).sqrt() * (-gap / (2 * vt)).exp()
        radius = (c*c/4 + ni*ni).sqrt()
        n, p = radius + c/2, radius - c/2
        return float(n), float(p), float(vt * (n/ni).ln())


def make_sim(shape=(7, 1, 1), graded=False, temperature=300.0):
    spans = (1e-6, 2e-7, 3e-7)
    axes = [span * np.linspace(0.0, 1.0, count)**(1.3 if graded else 1.0)
            for span, count in zip(spans, shape)]
    mesh = StructuredGrid(tuple((0.0, span) for span in spans), *shape, axes=axes)
    size = mesh.npts()
    mesh.fields.update(doping=np.zeros(size), Nc=np.full(size, 1e10),
                       Nv=np.full(size, 1e10), Eg=np.zeros(size),
                       epsilon=np.full(size, 11.7*8.854187817e-12),
                       mu_n=np.full(size, .1), mu_p=np.full(size, .05))
    sim = Simulator(mesh, temperature=temperature)
    return sim


@pytest.mark.parametrize('ratio', [0., -1e-8, 1e-8, -.25, .25, -1., 1., -20., 20., -1e10, 1e10])
@pytest.mark.parametrize('temperature', [200., 300., 450.])
@pytest.mark.parametrize('asymmetric_dos', [False, True])
def test_named_contact_matches_independent_neutral_reservoir(ratio, temperature, asymmetric_dos):
    sim = make_sim(temperature=temperature)
    mesh = sim.mesh
    if asymmetric_dos:
        mesh.fields['Nc'][:] = 3e16
        mesh.fields['Nv'][:] = 7e15
        mesh.fields['Eg'][:] = .5
    nc, nv = mesh.fields['Nc'][0]*1e6, mesh.fields['Nv'][0]*1e6
    gap = mesh.fields['Eg'][0]
    ni = np.sqrt(nc*nv)*np.exp(-gap/(2*sim.VT))
    mesh.fields['doping'][:] = ratio*ni/1e6
    mask = np.arange(mesh.npts()) % 2 == 0
    mesh.fields['contact_reservoir'] = mask
    sim.set_material_from_mesh()
    observer = Capture(sim._sim)
    sim._sim = observer
    sim.set_contact('reservoir', .07)
    calls = {name: args[0] for name, args, _ in observer.calls
             if name in ('set_electron_bc', 'set_hole_bc', 'set_dirichlet_potential')}
    expected_nodes = set(np.flatnonzero(mask))
    for name in ('set_electron_bc', 'set_hole_bc', 'set_dirichlet_potential'):
        assert set(calls[name]) == expected_nodes
    n, p, phi = equilibrium(mesh.fields['doping'][0]*1e6, nc, nv, gap, sim.VT)
    for i in expected_nodes:
        assert calls['set_electron_bc'][i] == pytest.approx(n, rel=2e-13)
        assert calls['set_hole_bc'][i] == pytest.approx(p, rel=2e-13)
        assert calls['set_dirichlet_potential'][i] == pytest.approx(.07+phi, abs=2e-15, rel=2e-13)


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('graded', [False, True])
@pytest.mark.parametrize('newton', [False, True])
@pytest.mark.parametrize('ratio', [-1., 0., 1.])
def test_public_unseeded_low_doping_resistor_matches_exact_solution(axis, graded, newton, ratio):
    shape = tuple(7 if a == axis else 1 for a in range(3))
    sim = make_sim(shape, graded)
    mesh = sim.mesh
    mesh.fields['doping'][:] = ratio*1e10
    mesh.fields['contact_left'] = np.arange(mesh.npts()) == 0
    mesh.fields['contact_right'] = np.arange(mesh.npts()) == mesh.npts()-1
    sim.set_material_from_mesh()
    sim.set_quantum(False)
    sim._sim.set_recombination(np.full(mesh.npts(), 1e100), np.full(mesh.npts(), 1e100))
    sim.set_contact('left', .012)
    sim.set_contact('right', -.003)
    sim.set_use_newton(newton)
    sim._sim.set_newton_primary(newton)
    sim.set_newton_log_space(newton)
    # No user initial guess or continuation is supplied. The native core uses
    # its default local-equilibrium initializer and performs one public run.
    result = sim.run(max_iter=100, tol=1e-10, physical_step=False)
    assert result['converged'] and result['valid'] and result['target_reached']
    assert result['continuation_retries'] == 0 and result['continuation_helper_solves'] == 1
    n, p, offset = equilibrium(ratio*1e16, 1e16, 1e16, 0., sim.VT)
    coords = mesh.axis_coordinates()[axis]
    phi = offset + .012 - .015*(coords-coords[0])/(coords[-1]-coords[0])
    np.testing.assert_allclose(result['phi'], phi, rtol=2e-8, atol=2e-10)
    np.testing.assert_allclose(result['n'], n, rtol=2e-7)
    np.testing.assert_allclose(result['p'], p, rtol=2e-7)
    spans = [hi-lo for lo, hi in [(mesh.xmin, mesh.xmax), (mesh.ymin, mesh.ymax), (mesh.zmin, mesh.zmax)]]
    area = np.prod([span for a, span in enumerate(spans) if a != axis])
    q = float(native_constants()['elementary_charge_C'])
    expected = q*(.1*n+.05*p)*.015/spans[axis]*area
    actual = terminal_currents_native(sim, result)
    assert actual == pytest.approx(dict(left=expected, right=-expected), rel=3e-7, abs=0.)
    check = ConservationTest(check_energy=False, current_atol_A=0., tolerance=1e-6)
    assert check.run(lambda: dict(result, terminal_currents_A=actual)).passed
    broken = dict(actual, right=actual['right']*.8)
    assert not check.run(lambda: dict(result, terminal_currents_A=broken)).passed
    print(json.dumps(dict(ohmic_resistor=True, profile=native_constants()['profile'], axis=axis,
                          graded=graded, newton=newton, doping_ratio=ratio, converged=True,
                          user_initial_guess=False, terminal_currents_A=actual, expected_current_A=expected,
                          max_current_error=max(abs(actual['left']-expected), abs(actual['right']+expected))/expected)))


@pytest.mark.parametrize('defect', ['nan_doping', 'inf_doping', 'zero_dos', 'intrinsic_underflow'])
def test_invalid_ohmic_equilibrium_is_rejected_before_setting_native_boundaries(defect):
    sim = make_sim()
    sim.mesh.fields['contact_left'] = np.arange(sim.mesh.npts()) == 0
    if defect.endswith('doping'):
        sim.mesh.fields['doping'][0] = np.nan if defect.startswith('nan') else np.inf
    elif defect == 'zero_dos':
        sim.mesh.fields['Nc'][0] = 0.0
    else:
        sim.mesh.fields['Eg'][0] = 10000.
    observer = Capture(sim._sim)
    sim._sim = observer
    with pytest.raises(ValueError, match='Ohmic'):
        sim.set_contact('left', 0.)
    assert not any(name in ('set_dirichlet_potential', 'set_electron_bc', 'set_hole_bc')
                   for name, _, _ in observer.calls)


@pytest.mark.parametrize('workfunction', [None, 4.6])
def test_mixed_material_electrode_only_pins_semiconductor_carriers(workfunction):
    sim = make_sim()
    mesh = sim.mesh
    semiconductor = np.arange(mesh.npts()) % 2 == 1
    mesh.fields['mu_n'][~semiconductor] = 0.0
    mesh.fields['mu_p'][~semiconductor] = 0.0
    mesh.fields['Nc'][~semiconductor] = 0.0
    mesh.fields['Nv'][~semiconductor] = 0.0
    mesh.fields['Eg'][:] = .5
    mesh.fields['chi'] = np.full(mesh.npts(), 4.0)
    mesh.fields['contact_mixed'] = np.ones(mesh.npts(), dtype=bool)
    observer = Capture(sim._sim)
    sim._sim = observer
    sim.set_contact('mixed', .04, workfunction=workfunction)
    calls = {name: args[0] for name, args, _ in observer.calls
             if name in ('set_electron_bc', 'set_hole_bc', 'set_dirichlet_potential')}
    assert set(calls['set_dirichlet_potential']) == set(range(mesh.npts()))
    for name in ('set_electron_bc', 'set_hole_bc'):
        assert set(calls[name]) == set(np.flatnonzero(semiconductor))
        assert all(np.isfinite(value) and value > 0.0 for value in calls[name].values())
    for i in np.flatnonzero(~semiconductor):
        assert calls['set_dirichlet_potential'][i] == .04
