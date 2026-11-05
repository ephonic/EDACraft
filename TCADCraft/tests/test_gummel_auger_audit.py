"""Synthetic high-injection stress: Auger must be resolved in each audit row."""
import numpy as np
import pytest
from test_native_nonlinear_history import make_transport


@pytest.mark.parametrize('axis', [0, 1, 2])
def test_resolved_auger_source_cannot_be_omitted_from_returned_state_audit(axis):
    # This tests the classical numerical operator, not material validity of
    # Boltzmann statistics at this deliberately extreme injected density.
    sim = make_transport(axis, budget=0)
    density = 1e27
    sim.set_mobility(np.full(3, .1), np.full(3, .1))
    sim.set_doping(np.array([0., density, 0.]))
    sim.set_initial_guess(np.zeros(3), np.array([1e19, density, 1e19]),
                          np.array([1e19, density, 1e19]))
    initial_srh = (density**2-1e38)/(3e-9*(density+1e19))
    initial_auger = (2.8e-43+9.9e-44)*density*(density**2-1e38)
    generation = initial_srh+initial_auger+2*.1*.02585/1e-14*(density-1e19)
    sim.set_optical_generation(np.full(3, generation))
    sim.set_recombination(np.full(3, 1e-9), np.full(3, 2e-9))
    sim.set_auger_enabled(True)
    sim.set_auger_params(2.8e-43, 9.9e-44)
    result = sim.solve()
    audit = result['steady_equation_audit']
    assert audit['available'] and not result['converged']
    n, p = result['n'][1], result['p'][1]
    ni, tn, tp = 1e19, 1e-9, 2e-9
    den = tp*(n+ni)+tn*(p+ni)
    srh = (n*p-ni*ni)/den
    auger = (2.8e-43*n+9.9e-44*p)*(n*p-ni*ni)
    assert auger > 100*abs(srh)
    derivatives = ((p*(tp*ni+tn*(p+ni))+tp*ni*ni)/den**2,
                   (n*(tn*ni+tp*(n+ni))+tn*ni*ni)/den**2)
    for label, density, mobility, dr in zip(('electron', 'hole'), (n, p), (.1, .1), derivatives):
        d = mobility*.02585/1e-7
        lhs = (2*d+dr*1e-7)*density-2*d*ni
        def residual(rate):
            rhs = (generation-rate+dr*density)*1e-7
            return abs(lhs-rhs)/(abs(rhs)+abs((2*d+dr*1e-7)*density)+2*d*ni)
        expected = residual(srh+auger)
        assert abs(expected-residual(srh)) > .01
        assert audit[label+'_backward_error_linf'] == pytest.approx(expected, rel=2e-13, abs=2e-16)
    assert not audit['equations_pass'] and not audit['physical_validated']
