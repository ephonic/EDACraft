"""2D parabolic edge thermionic supply, pinned SBH and coupled DD."""
import itertools
import numpy as np
import mpmath as mp
import pytest
from tcad.material import mos2_sheet,graphene_sheet
from tcad.material.sheet import Q,KB,HBAR,M0
from tcad.solver.sheet_thermionic import half_difference,thermionic_current
from tcad.solver.sheet_drift_diffusion import SheetDriftDiffusion
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion
from test_sheet_drift_diffusion import ledgers
mp.mp.dps=80


def device(dielectric=False,barrier=(.08,.12),scheme='diffusion_enhanced',width=100e-9,temperature=300.):
    material=mos2_sheet(reference_eV=-.9);seed=material.statistics(temperature_K=temperature)
    x=(.5-.5*np.cos(np.linspace(0,np.pi,9)))*200e-9;y=np.array([0.,.3,1.])*width
    kwargs=dict(mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,doping_m2=float(seed.n_m2-seed.p_m2),
        sheet_permittivity_F=4e-20,temperature_K=temperature,thermionic_barrier_n_eV=barrier,transport_scheme=scheme)
    if dielectric:
        z=np.linspace(-16e-9,16e-9,7);eps=np.r_[np.full(3,3.9),np.full(3,9.)][:,None,None]*8.8541878128e-12
        return DielectricSheetDriftDiffusion(x,y,z,material,sheet_index=3,permittivity_F_m=eps,**kwargs)
    return SheetDriftDiffusion(x,y,material,gate_capacitance_F_m2=.006,**kwargs)


def drive(sim,dielectric,uniform=False):
    gate=-.12 if uniform else -.12*np.outer([.6,.8,1.],np.sin(np.pi*sim.x/sim.x[-1])**2)
    return dict(top_gate_voltage_V=gate,bottom_gate_voltage_V=0.) if dielectric else dict(gate_voltage_V=gate)


@pytest.mark.parametrize('a,b',[(-600.,-599.),(-200.,-180.),(-40.,-40.+1e-9),(-10.,-9.),(0.,0.),(0.,1e-10),(5.,-5.),(20.,21.),(100.,101.),(200.,199.)])
def test_half_integral_and_derivative_against_80_digit_polylog(a,b):
    diff,derivative=half_difference(a,b)
    H=lambda x:mp.re(-mp.gamma(mp.mpf('1.5'))*mp.polylog(mp.mpf('1.5'),-mp.exp(mp.mpf(x))))
    expected=float(H(a)-H(b));slope=float(mp.diff(H,mp.mpf(a)))
    assert abs(float(diff)-expected)<1e-11*max(abs(expected),1e-300)
    assert abs(float(derivative)/slope-1)<1e-11


@pytest.mark.parametrize('sign,drop,barrier',itertools.product((-1,1),(-.1,-1e-16,0.,1e-16,.1),(0.,.15)))
def test_current_slope_balance_and_tiny_drop(sign,drop,barrier):
    I,G=thermionic_current(drop,barrier,temperature_K=300.,mass_m0=.5,degeneracy=4,width_m=1e-7,sign=sign)
    vt=mp.mpf(KB*300/Q);b=-mp.mpf(barrier)/vt;delta=sign*mp.mpf(drop)/vt
    H=lambda x:mp.re(-mp.gamma(mp.mpf('1.5'))*mp.polylog(mp.mpf('1.5'),-mp.exp(x)))
    pref=Q*4*np.sqrt(M0)*(KB*300)**1.5/(2*np.pi**2*HBAR**2)*1e-7
    expected=float(sign*mp.mpf(pref)*(H(b+delta)-H(b)))
    slope=float(mp.mpf(pref)/vt*mp.diff(H,b+delta))
    assert abs(float(I)-expected)<1e-11*max(abs(expected),1e-300)
    assert abs(float(G)/slope-1)<1e-11
    assert I*drop>=0
    if drop==0:assert I==0.


@pytest.mark.parametrize('temperature',(150.,300.,600.))
def test_nondegenerate_2d_T_three_halves_limit(temperature):
    # Hold reduced barrier fixed: isolate the lateral 2D T**1.5 prefactor.
    barrier=30*KB*temperature/Q;drop=KB*temperature/Q
    I,_=thermionic_current(drop,barrier,temperature_K=temperature,mass_m0=.5,degeneracy=4,width_m=1e-7,sign=1)
    expected=Q*4*np.sqrt(M0)*(KB*temperature)**1.5/(2*np.pi**2*HBAR**2)*1e-7*np.sqrt(np.pi)/2*np.exp(-30)*np.expm1(1.)
    assert abs(I/expected-1)<1e-11


@pytest.mark.parametrize('bad',[-.1,1.81,np.nan,np.inf,True,1j,'1',[.1],[[.1,.2]]])
def test_invalid_barriers(bad):
    with pytest.raises(ValueError):device(barrier=bad)


def test_graphene_and_duplicate_models_rejected():
    kwargs=dict(gate_capacitance_F_m2=.006,mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,thermionic_barrier_n_eV=.1)
    with pytest.raises(ValueError):SheetDriftDiffusion([0.,1.],[0.,1.],graphene_sheet(),**kwargs)
    with pytest.raises(ValueError):SheetDriftDiffusion([0.,1.],[0.,1.],mos2_sheet(),contact_resistance_ohm_m=.01,**kwargs)


@pytest.mark.parametrize('a,b',[(-601.,0.),(0.,201.)])
def test_unqualified_supply_range_rejected(a,b):
    with pytest.raises(FloatingPointError):half_difference(a,b)


@pytest.mark.parametrize('dielectric,scheme,bias',itertools.product((False,True),('midpoint','diffusion_enhanced'),(-.02,0.,.02)))
def test_coupled_pinned_barriers_and_ledgers(dielectric,scheme,bias):
    sim=device(dielectric,scheme=scheme)
    r=sim.solve(**drive(sim,dielectric),drain_voltage_V=bias,max_iter=120,tolerance=1e-12)
    ledgers(r);assert r['contact_model']=='parabolic_fd_thermionic_edge'
    assert 'contact_resistance_ohm_m' not in r
    for a,(nodes,V) in enumerate(((sim.left,0.),(sim.right,bias))):
        phi=r['phi_V'].ravel()[nodes];Ec=sim.material.reference_eV+sim.material.gap_eV/2-phi
        np.testing.assert_allclose(Ec+V,sim.thermionic_barrier_n_eV[a],atol=1e-14,rtol=0)
        assert abs(r['terminal_currents_into_sheet_A'][('source','drain')[a]]-r['sheet_terminal_currents_into_sheet_A'][('source','drain')[a]])<1e-8*max(abs(r['terminal_currents_into_sheet_A']['drain']),1e-20)
    assert r['contact_dissipation_W']>=0
    if bias==0:assert np.max(abs(r['edge_currents_A']))==0. and np.max(abs(r['contact_currents_into_sheet_A']))==0.


@pytest.mark.parametrize('dielectric',(False,True))
def test_thermionic_full_jacobian(dielectric):
    sim=device(dielectric);N=sim.size;rng=np.random.default_rng(503)
    u=rng.normal(0,.025,3*N);d=rng.normal(0,1,3*N);bc=(np.zeros(len(sim.contacts)),)*3
    gate=sim.dielectric.gate_drive(top_gate_voltage_V=-.1,bottom_gate_voltage_V=0.) if dielectric else np.full(N,-.1)
    _,scale,J,*_=sim._evaluate(u,gate,bc);h=2e-7
    fd=(sim._evaluate(u+h*d,gate,bc,False)[0]-sim._evaluate(u-h*d,gate,bc,False)[0])/(2*h)
    assert np.max(abs((J@d-fd)/scale))<2e-5


@pytest.mark.parametrize('dielectric',(False,True))
def test_uniform_width_scaling(dielectric):
    currents=[]
    for width in (100e-9,300e-9):
        sim=device(dielectric,width=width)
        r=sim.solve(**drive(sim,dielectric,True),drain_voltage_V=.02,max_iter=120,tolerance=1e-12)
        ledgers(r);currents.append(r['terminal_currents_into_sheet_A']['drain'])
    assert abs(currents[1]/currents[0]-3)<1e-8


def test_barrier_parameters_owned_and_returned_copy():
    barrier=np.array([.08,.12]);sim=device(barrier=barrier);barrier[:]=.2
    np.testing.assert_array_equal(sim.thermionic_barrier_n_eV,[.08,.12])
    r=sim.solve(**drive(sim,False),drain_voltage_V=.02,max_iter=120)
    r['thermionic_barrier_n_eV'][:]=.3
    np.testing.assert_array_equal(sim.thermionic_barrier_n_eV,[.08,.12])
