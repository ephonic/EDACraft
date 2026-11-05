"""Cold resistor solves must retain descent after quasi-Fermi trust clipping."""
import re
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator, native_constants
from test_transport_parameter_guard import resistor


H = 1e-6/8
VT = .0258520


def cold_bar(axis=0, ptype=False, bias=.2, optical=False, budget=60):
    shape = [1, 1, 1];shape[axis] = 9
    sim = PyDeviceSimulator(*shape, H, H, H)
    sim.set_permittivity(np.full(9, 8.854187817e-12*11.7))
    sim.set_mobility(np.full(9,.1), np.full(9,.035))
    sim.set_doping(np.full(9, -1e21 if ptype else 1e21))
    sim.set_thermal_voltage(VT)
    sim.set_recombination(np.full(9,1e-7),np.full(9,1e-7))
    sim.set_effective_dos(np.full(9,2.8e25),np.full(9,1.04e25))
    sim.set_bandgap(np.full(9,1.12))
    sim.set_dirichlet_potential({0:bias,8:0.})
    sim.set_electron_bc({0:1e5 if ptype else 1e21,8:1e5 if ptype else 1e21})
    sim.set_hole_bc({0:1e21 if ptype else 1e5,8:1e21 if ptype else 1e5})
    if optical:sim.set_optical_generation(np.full(9,1e20))
    sim.set_use_newton(True);sim.set_newton_primary(True)
    sim.set_gummel_max_iter(budget)
    sim.set_tolerance(1e-8)
    sim.set_nonlinear_history_enabled(True)
    return sim


def independent_equations(r, axis, ptype, bias, optical):
    q = float(native_constants()['elementary_charge_C'])
    phi,n,p = (np.asarray(r[key]) for key in ('phi','n','p'))
    assert np.all(np.isfinite(np.r_[phi,n,p]))
    assert np.all(n>0) and np.all(p>0)
    np.testing.assert_allclose(phi[[0,8]],[bias,0.],rtol=0,atol=1e-12)
    np.testing.assert_allclose(n[[0,8]],1e5 if ptype else 1e21,rtol=1e-10)
    np.testing.assert_allclose(p[[0,8]],1e21 if ptype else 1e5,rtol=1e-10)
    delta = np.diff(phi)/VT
    # The expected biased bars are away from the removable Bernoulli zero.
    assert np.min(np.abs(delta))>1e-6
    bp = delta/np.expm1(delta);bm = -delta/np.expm1(-delta)
    fn = .1*VT/H*(n[:-1]*bm-n[1:]*bp)
    fp = .035*VT/H*(p[:-1]*bp-p[1:]*bm)
    label='xyz'[axis]
    np.testing.assert_allclose(r['Jn_'+label][:-1],-q*fn,rtol=2e-11,atol=1e-8)
    np.testing.assert_allclose(r['Jp_'+label][:-1],q*fp,rtol=2e-11,atol=1e-8)
    current=q*(fp-fn)
    assert np.ptp(current)/np.max(np.abs(current))<1e-8
    # Independent finite-volume Poisson and SG+SRH balance at returned nodes.
    eps=8.854187817e-12*11.7
    doping=-1e21 if ptype else 1e21
    charge=q*(n[1:-1]-p[1:-1]-doping)
    diagonal=2*eps/H**2*phi[1:-1]
    neighbors=eps/H**2*(phi[:-2]+phi[2:])
    poisson=diagonal-neighbors+charge
    assert np.max(np.abs(poisson)/(np.abs(diagonal)+np.abs(neighbors)+q*(n[1:-1]+p[1:-1]+abs(doping))))<1e-8
    # intrinsic_density uses its documented eV/K constant and temperature,
    # independently of the explicitly supplied transport VT.
    ni=np.sqrt(2.8e25*1.04e25)*np.exp(-1.12/(2*8.617333262e-5*300))
    srh=(n[1:-1]*p[1:-1]-ni**2)/(1e-7*(n[1:-1]+p[1:-1]+2*ni))
    source=(srh-(1e20 if optical else 0))*H
    for c,mu,plus,minus in [(n,.1,bm,bp),(p,.035,bp,bm)]:
        diag=mu*VT/H*(minus[:-1]+plus[1:])*c[1:-1]
        nbr=mu*VT/H*(plus[:-1]*c[:-2]+minus[1:]*c[2:])
        backward=np.abs(diag-nbr+source)/(np.abs(diag)+np.abs(nbr)+np.abs(source))
        assert np.max(backward)<1e-8


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('ptype',[False,True])
@pytest.mark.parametrize('bias',[-.2,.2])
@pytest.mark.parametrize('optical',[False,True])
def test_cold_bar_converges_with_independent_equations(axis,ptype,bias,optical):
    sim=cold_bar(axis,ptype,bias,optical)
    assert sim.get_newton_log_density_update()=='exponential'
    result=sim.solve()
    assert result['converged']
    independent_equations(result,axis,ptype,bias,optical)


def test_original_stall_exercises_accepted_exponential_second_search(monkeypatch,capfd):
    monkeypatch.setenv('TCAD_NEWTON_VERBOSE','1')
    _,sim=resistor();sim.set_use_newton(True);sim.set_newton_primary(True)
    sim.set_tolerance(1e-8)
    result=sim.solve()
    output=capfd.readouterr().out
    steps=re.findall(r'\[descent fallback\] policy=exponential scale=([^ ]+) alpha=([^\s]+)',output)
    assert steps and any(float(alpha)>0 for _,alpha in steps)
    assert result['converged']
    independent_equations(result,0,False,.2,False)


def test_original_default_tolerance_also_converges():
    _,sim=resistor();sim.set_use_newton(True);sim.set_newton_primary(True)
    result=sim.solve()
    assert result['converged']
    np.testing.assert_allclose(result['phi'],np.linspace(.2,0.,9),rtol=0,atol=1e-10)
    np.testing.assert_allclose(result['n'],1e21,rtol=1e-10)


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('budget',[0,1])
def test_insufficient_budget_remains_failure(axis,budget):
    result=cold_bar(axis,budget=budget).solve()
    assert not result['converged']
    assert all(np.all(np.isfinite(result[key])) for key in ('phi','n','p'))


@pytest.mark.parametrize('model',['ii','btbt'])
def test_stiff_sources_do_not_enter_new_exponential_fallback(model,monkeypatch,capfd):
    monkeypatch.setenv('TCAD_NEWTON_VERBOSE','1')
    sim=cold_bar(budget=1)
    if model=='ii':sim.set_ii_params(10.,0.,20.,0.);sim.set_ii_enabled(True)
    else:sim.set_btbt_enabled(True)
    result=sim.solve()
    assert not result['converged']
    assert '[descent fallback] policy=exponential' not in capfd.readouterr().out
