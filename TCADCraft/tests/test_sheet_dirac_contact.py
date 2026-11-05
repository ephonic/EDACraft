"""Gapless Dirac finite mode-supply contacts and independent references."""
import itertools
import numpy as np
import mpmath as mp
import pytest
from tcad.material import graphene_sheet,mos2_sheet
from tcad.material.sheet import Q,KB,HBAR
from tcad.solver.sheet_dirac_contact import linear_difference,dirac_edge_current
from tcad.solver.sheet_drift_diffusion import SheetDriftDiffusion
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion
from test_sheet_drift_diffusion import ledgers
mp.mp.dps=80


def device(dielectric=False,offset=(-.04,.06),scheme='diffusion_enhanced',width=100e-9):
    material=graphene_sheet();x=(.5-.5*np.cos(np.linspace(0,np.pi,9)))*200e-9;y=np.array([0.,.3,1.])*width
    common=dict(mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,sheet_permittivity_F=4e-20,
        dirac_contact_offset_eV=offset,transport_scheme=scheme)
    if dielectric:
        z=np.linspace(-16e-9,16e-9,7);eps=np.r_[np.full(3,3.9),np.full(3,9.)][:,None,None]*8.8541878128e-12
        return DielectricSheetDriftDiffusion(x,y,z,material,sheet_index=3,permittivity_F_m=eps,**common)
    return SheetDriftDiffusion(x,y,material,gate_capacitance_F_m2=.006,**common)


def drive(sim,dielectric,amplitude=-.12,uniform=False):
    gate=amplitude if uniform else amplitude*np.outer([.6,.8,1.],np.sin(np.pi*sim.x/sim.x[-1])**2)
    return dict(top_gate_voltage_V=gate,bottom_gate_voltage_V=0.) if dielectric else dict(gate_voltage_V=gate)


@pytest.mark.parametrize('a,b',[(-600.,-599.),(-200.,-180.),(-40.,-40.+1e-9),(-10.,-9.),(0.,0.),(0.,1e-10),(5.,-5.),(20.,21.),(100.,101.),(200.,199.)])
def test_linear_integral_and_derivative_80_digits(a,b):
    delta,slope=linear_difference(a,b)
    H=lambda x:mp.re(-mp.polylog(2,-mp.exp(mp.mpf(x))))
    reference=float(H(a)-H(b));derivative=float(mp.log1p(mp.exp(mp.mpf(a))))
    assert abs(float(delta)-reference)<1e-11*max(abs(reference),1e-300)
    assert abs(float(slope)/derivative-1)<1e-11


@pytest.mark.parametrize('sign,drop,offset',itertools.product((-1,1),(-.1,-1e-16,0.,1e-16,.1),(-.15,0.,.15)))
def test_current_and_derivative_80_digits(sign,drop,offset):
    I,G=dirac_edge_current(drop,offset,temperature_K=300.,fermi_velocity_m_s=1e6,degeneracy=4,width_m=1e-7,sign=sign)
    vt=mp.mpf(KB*300/Q);b=-mp.mpf(offset)/vt;delta=sign*mp.mpf(drop)/vt
    H=lambda x:mp.re(-mp.polylog(2,-mp.exp(x)))
    pref=Q*4*(KB*300)**2/(2*np.pi**2*HBAR**2*1e6)*1e-7
    expected=float(sign*mp.mpf(pref)*(H(b+delta)-H(b)))
    slope=float(mp.mpf(pref)/vt*mp.log1p(mp.exp(b+delta)))
    assert abs(float(I)-expected)<1e-11*max(abs(expected),1e-300)
    assert abs(float(G)/slope-1)<1e-11
    assert I*drop>=0
    if drop==0:assert I==0.


@pytest.mark.parametrize('temperature',(150.,300.,600.))
def test_nondegenerate_supply_from_density_and_angular_velocity(temperature):
    # Independently integrate positive velocity angles: one-way flux=n*vF/pi.
    vt=KB*temperature/Q;velocity=1e6;g=4;width=1e-7
    n2D=g/(2*np.pi)*(KB*temperature/(HBAR*velocity))**2*np.exp(-30.)
    expected=Q*n2D*velocity/np.pi*width*np.expm1(1.)
    I,_=dirac_edge_current(vt,30*vt,temperature_K=temperature,fermi_velocity_m_s=velocity,degeneracy=g,width_m=width,sign=1)
    assert abs(I/expected-1)<1e-11


@pytest.mark.parametrize('dielectric,scheme',itertools.product((False,True),('midpoint','diffusion_enhanced')))
def test_neutral_small_signal_independent_series_network(dielectric,scheme):
    sim=device(dielectric,offset=0.,scheme=scheme);st=sim.material.statistics();width=sim.y[-1]-sim.y[0]
    densities=np.array([float(st.n_m2),float(st.p_m2)]);channel=(sim.x[-1]-sim.x[0])/(Q*np.array([.02,.01])*densities*width)
    # Each contact: derivative of the complete FD mode supply at the Dirac point.
    contact_G=Q*Q*4*KB*300*np.log(2.)/(2*np.pi**2*HBAR**2*1e6)*width
    expected=float(np.sum(1/(channel+2/contact_G)))
    rs=[sim.solve(**drive(sim,dielectric,0.),drain_voltage_V=v,max_iter=120,tolerance=1e-13) for v in (-1e-5,1e-5)]
    for r in rs:ledgers(r)
    derivative=(rs[1]['terminal_currents_into_sheet_A']['drain']-rs[0]['terminal_currents_into_sheet_A']['drain'])/2e-5
    assert abs(derivative/expected-1)<1e-6


@pytest.mark.parametrize('bad',[np.nan,np.inf,True,1j,'1',[.1],[[.1,.2]],np.ones(3)])
def test_invalid_offsets(bad):
    with pytest.raises(ValueError):device(offset=bad)


def test_material_and_duplicate_models_rejected():
    common=dict(gate_capacitance_F_m2=.006,mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,dirac_contact_offset_eV=0.)
    with pytest.raises(ValueError):SheetDriftDiffusion([0.,1.],[0.,1.],mos2_sheet(),**common)
    with pytest.raises(ValueError):SheetDriftDiffusion([0.,1.],[0.,1.],graphene_sheet(),contact_resistance_ohm_m=.01,**common)
    with pytest.raises(ValueError):SheetDriftDiffusion([0.,1.],[0.,1.],graphene_sheet(),thermionic_barrier_n_eV=0.,**common)


@pytest.mark.parametrize('a,b',[(-601.,0.),(0.,201.)])
def test_outside_qualified_range_rejected(a,b):
    with pytest.raises(FloatingPointError):linear_difference(a,b)


@pytest.mark.parametrize('dielectric,scheme,offset,bias',itertools.product((False,True),('midpoint','diffusion_enhanced'),((0.,0.),(-.1,-.1),(-.08,.12)),(-.02,0.,.02)))
def test_coupled_alignment_and_ledgers(dielectric,scheme,offset,bias):
    sim=device(dielectric,offset=offset,scheme=scheme)
    r=sim.solve(**drive(sim,dielectric),drain_voltage_V=bias,max_iter=120,tolerance=1e-12)
    ledgers(r);assert r['contact_model']=='dirac_fd_mode_supply_edge'
    assert 'thermionic_barrier_n_eV' not in r and 'contact_resistance_ohm_m' not in r
    for a,(nodes,V) in enumerate(((sim.left,0.),(sim.right,bias))):
        ED=sim.material.reference_eV-r['phi_V'].ravel()[nodes]
        np.testing.assert_allclose(ED+V,offset[a],atol=1e-14,rtol=0.)
        name=('source','drain')[a]
        assert abs(r['terminal_currents_into_sheet_A'][name]-r['sheet_terminal_currents_into_sheet_A'][name])<1e-8*max(abs(r['terminal_currents_into_sheet_A']['drain']),1e-20)
    assert r['contact_dissipation_W']>=0
    if bias==0:assert np.max(abs(r['edge_currents_A']))==0. and np.max(abs(r['contact_currents_into_sheet_A']))==0.


@pytest.mark.parametrize('dielectric',(False,True))
def test_full_jacobian(dielectric):
    sim=device(dielectric);N=sim.size;rng=np.random.default_rng(504)
    u=rng.normal(0,.025,3*N);d=rng.normal(0,1,3*N);bc=(np.zeros(len(sim.contacts)),)*3
    gate=sim.dielectric.gate_drive(top_gate_voltage_V=-.1,bottom_gate_voltage_V=0.) if dielectric else np.full(N,-.1)
    _,scale,J,*_=sim._evaluate(u,gate,bc);h=2e-7
    fd=(sim._evaluate(u+h*d,gate,bc,False)[0]-sim._evaluate(u-h*d,gate,bc,False)[0])/(2*h)
    assert np.max(abs((J@d-fd)/scale))<2e-5


@pytest.mark.parametrize('dielectric',(False,True))
def test_width_scaling(dielectric):
    currents=[]
    for width in (100e-9,300e-9):
        sim=device(dielectric,width=width)
        r=sim.solve(**drive(sim,dielectric,uniform=True),drain_voltage_V=.02,max_iter=120,tolerance=1e-12)
        ledgers(r);currents.append(r['terminal_currents_into_sheet_A']['drain'])
    assert abs(currents[1]/currents[0]-3)<1e-8


def test_parameter_ownership():
    offset=np.array([-.04,.06]);sim=device(offset=offset);offset[:]=.2
    np.testing.assert_array_equal(sim.dirac_contact_offset_eV,[-.04,.06])
    assert not sim.dirac_contact_offset_eV.flags.writeable
    r=sim.solve(**drive(sim,False),drain_voltage_V=.02,max_iter=120)
    r['dirac_contact_offset_eV'][:]=.3
    np.testing.assert_array_equal(sim.dirac_contact_offset_eV,[-.04,.06])
