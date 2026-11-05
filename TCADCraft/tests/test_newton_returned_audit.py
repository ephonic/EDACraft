"""Optional SG audit must score returned Newton/rollback fields independently."""
import numpy as np
import pytest

from tcad.core import native_constants
from test_native_nonlinear_history import make_transport
from test_newton_descent_fallback import cold_bar, independent_equations
from test_ii_newton_merit import avalanche_bar, independent_balance, MODELS, COEFFICIENTS


def same_value(a, b):
    if isinstance(a, np.ndarray):
        np.testing.assert_array_equal(a, b)
    elif isinstance(a, dict):
        assert a.keys() == b.keys()
        for k in a:
            same_value(a[k], b[k])
    elif isinstance(a, (list, tuple)):
        assert len(a) == len(b)
        for x, y in zip(a, b):
            same_value(x, y)
    else:
        assert a == b


def check_audit(r):
    a = r['steady_equation_audit']
    assert a['available'] and a['unavailable_reason'] is None
    assert a['scope'] == 'classical_Newton_SG_final_returned_state'
    rows = [a[k] for k in ('poisson_scaled_linf', 'electron_backward_error_linf',
                           'hole_backward_error_linf')]
    assert np.all(np.isfinite(rows)) and min(rows) >= 0.
    assert a['equations_pass'] == (max(rows) < a['equation_gate'])
    assert not a['complete_device_energy'] and not a['physical_validated']
    return a


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('ptype', [False, True])
@pytest.mark.parametrize('bias', [-.2, .2])
@pytest.mark.parametrize('optical', [False, True])
def test_audit_does_not_change_solution_or_earned_verdict(axis, ptype, bias, optical):
    default = cold_bar(axis, ptype, bias, optical).solve()
    audited = cold_bar(axis, ptype, bias, optical).solve(audit_newton=True)
    assert default['converged'] and audited['converged']
    same_value({k: v for k, v in default.items() if k != 'steady_equation_audit'},
               {k: v for k, v in audited.items() if k != 'steady_equation_audit'})
    assert not default['steady_equation_audit']['available']
    assert check_audit(audited)['equations_pass']
    independent_equations(audited, axis, ptype, bias, optical)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('ptype', [False, True])
@pytest.mark.parametrize('bias', [-.2, .2])
@pytest.mark.parametrize('model', MODELS[:2])
@pytest.mark.parametrize('coefficients', COEFFICIENTS)
def test_nonzero_ii_audit_keeps_full_source(axis, ptype, bias, model, coefficients):
    r = avalanche_bar(axis, ptype, bias, 'additive', model, coefficients).solve(audit_newton=True)
    assert r['converged'] and check_audit(r)['equations_pass']
    independent_balance(r, axis, ptype, bias, model, coefficients)


def reference_rows(r, generation, tn, tp, cn, cp):
    """Three-node FV equations, independent of native reassembly helpers."""
    phi, n, p = (r[k] for k in ('phi', 'n', 'p'))
    h, vt, ni = 1e-7, .02585, 1e19
    q = float(native_constants()['elementary_charge_C'])
    eps = 11.7*8.854187817e-12
    rhs = q*(p[1]-n[1]+1.5e18)
    charge = q*(n[1]+p[1]+1.5e18)
    poisson = abs(eps/h**2*(2*phi[1]-phi[0]-phi[2])-rhs)/(
        vt*4*eps/h**2+charge+abs(rhs))
    d = np.diff(phi)/vt
    bp = np.ones(2); bm = np.ones(2)
    active = np.abs(d) > 1e-12
    bp[active] = d[active]/np.expm1(d[active])
    bm[active] = -d[active]/np.expm1(-d[active])
    nn, pp = n[1], p[1]
    den = tp*(nn+ni)+tn*(pp+ni)
    srh = (nn*pp-ni**2)/den
    auger = (cn*nn+cp*pp)*(nn*pp-ni**2)
    drn = (pp*(tp*ni+tn*(pp+ni))+tp*ni**2)/den**2
    drp = (nn*(tn*ni+tp*(nn+ni))+tn*ni**2)/den**2
    carriers = []
    for c, mu, plus, minus, dr in [(n, .1, bm, bp, drn), (p, .05, bp, bm, drp)]:
        diagonal = (mu*vt/h*(minus[0]+plus[1])+dr*h)*c[1]
        left = mu*vt/h*plus[0]*c[0]
        right = mu*vt/h*minus[1]*c[2]
        rhs_c = (generation-srh-auger+dr*c[1])*h
        carriers.append(abs(diagonal-left-right-rhs_c)/(
            abs(diagonal)+abs(left)+abs(right)+abs(rhs_c)))
    return [poisson, *carriers]


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('generation', [0., 1e25])
@pytest.mark.parametrize('reaction', ['none', 'srh', 'srh_auger'])
@pytest.mark.parametrize('primary', [False, True])
@pytest.mark.parametrize('budget', [0, 1])
def test_failed_primary_and_hybrid_audit_actual_rollback(axis, generation, reaction, primary, budget):
    sim = make_transport(axis, budget, primary=primary, hybrid=not primary, generation=generation)
    tn, tp = (1e-9, 2e-9) if reaction != 'none' else (1e100, 1e100)
    sim.set_recombination(np.full(3, tn), np.full(3, tp))
    cn, cp = (2.8e-43, 9.9e-44) if reaction == 'srh_auger' else (0., 0.)
    sim.set_auger_enabled(bool(cn))
    if cn:
        sim.set_auger_params(cn, cp)
    r = sim.solve(audit_newton=True)
    assert not r['converged']
    a = check_audit(r)
    expected = reference_rows(r, generation, tn, tp, cn, cp)
    actual = [a[k] for k in ('poisson_scaled_linf', 'electron_backward_error_linf',
                            'hole_backward_error_linf')]
    np.testing.assert_allclose(actual, expected, rtol=2e-8, atol=2e-14)
    assert a['requested_update_tolerance'] == 1e-11 and a['equation_gate'] == 1e-8
    assert not a['equations_pass']


@pytest.mark.parametrize('feature', ['fermi', 'btbt', 'freeze_phi',
                                    'freeze_n', 'freeze_p', 'Nc', 'Nv', 'Eg', 'immobile', 'traps'])
def test_unsupported_physics_has_no_fabricated_rows(feature):
    sim = make_transport(primary=True, budget=0)
    if feature == 'quantum': sim.set_quantum_enabled(True)
    elif feature == 'fermi': sim.set_statistics_type(1)
    elif feature == 'btbt': sim.set_btbt_enabled(True)
    elif feature.startswith('freeze_'): getattr(sim, 'set_newton_'+feature)(True)
    elif feature in ('Nc', 'Nv'):
        nc = np.full(3, 1e19); nv = nc.copy()
        (nc if feature == 'Nc' else nv)[1] *= 2
        sim.set_effective_dos(nc, nv)
    elif feature == 'Eg': sim.set_bandgap(np.array([0., .1, 0.]))
    elif feature == 'immobile': sim.set_mobility(np.zeros(3), np.full(3, .05))
    elif feature == 'traps': sim.set_interface_traps(np.ones(3, dtype=np.int8), 1e14, 0.)
    r = sim.solve(audit_newton=True); a = r['steady_equation_audit']
    assert not a['available'] and a['unavailable_reason'] == 'unsupported_newton_audit_physics'
    for key in ('poisson_scaled_linf', 'electron_backward_error_linf', 'hole_backward_error_linf',
                'equation_gate', 'requested_update_tolerance', 'equations_pass'):
        assert a[key] is None


def test_audit_does_not_leak_to_next_default_call():
    sim = make_transport(primary=True)
    first = sim.solve(audit_newton=True); saved = dict(first['steady_equation_audit'])
    assert check_audit(first)['equations_pass']
    second = sim.solve()
    assert not second['steady_equation_audit']['available']
    assert first['steady_equation_audit'] == saved


@pytest.mark.parametrize('bad', [1, 'yes', None, np.nan, [], object()])
def test_invalid_audit_option_is_rejected_before_solving(bad):
    sim = make_transport(primary=True, budget=0)
    with pytest.raises(ValueError, match='audit_newton must be a boolean'):
        sim.solve(audit_newton=bad)


def test_public_run_forwards_optional_audit():
    from test_transport_parameter_guard import resistor
    owner, sim = resistor(public=True)
    sim.set_use_newton(True); sim.set_newton_primary(True)
    r = owner.run(max_iter=60, tol=1e-8, audit_newton=True)
    assert r['converged'] and check_audit(r)['equations_pass']
    independent_equations(r, 0, False, .2, False)


@pytest.mark.parametrize('bad', [1, 'yes', None, np.nan, [], object()])
def test_public_invalid_audit_option_is_atomic(bad):
    from test_transport_parameter_guard import resistor
    owner, _ = resistor(public=True)
    before = repr(owner.configuration_snapshot())
    with pytest.raises(ValueError, match='audit_newton must be a boolean'):
        owner.run(max_iter=1, audit_newton=bad)
    assert repr(owner.configuration_snapshot()) == before


@pytest.mark.parametrize('axis', [0, 1, 2])
def test_gummel_optional_request_retains_existing_audit(axis):
    same_value(make_transport(axis).solve(), make_transport(axis).solve(audit_newton=np.bool_(True)))
