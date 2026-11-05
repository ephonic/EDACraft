"""Finite electrochemical edge contacts; no thermionic assumptions."""
import itertools
import numpy as np
import pytest
from tcad.material import graphene_sheet, mos2_sheet
from tcad.material.sheet import Q
from tcad.solver.sheet_drift_diffusion import SheetDriftDiffusion
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion
from test_sheet_drift_diffusion import ledgers


def device(kind='graphene',dielectric=False,scheme='diffusion_enhanced',resistance=.003,width=100e-9,nx=9):
    material=graphene_sheet() if kind=='graphene' else mos2_sheet(reference_eV=-.9)
    x=(.5-.5*np.cos(np.linspace(0,np.pi,nx)))*200e-9
    y=np.array([0.,.3,1.])*width
    seed=material.statistics()
    common=dict(mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,
        doping_m2=float(seed.n_m2-seed.p_m2),sheet_permittivity_F=4e-20,
        transport_scheme=scheme,contact_resistance_ohm_m=resistance)
    if dielectric:
        z=np.linspace(-16e-9,16e-9,7)
        eps=np.r_[np.full(3,3.9),np.full(3,9.)][:,None,None]*8.8541878128e-12
        return DielectricSheetDriftDiffusion(x,y,z,material,sheet_index=3,permittivity_F_m=eps,**common)
    return SheetDriftDiffusion(x,y,material,gate_capacitance_F_m2=.006,**common)


def drive(sim,dielectric,amplitude=-.12):
    gate=amplitude*np.outer(np.array([.6,.8,1.]),np.sin(np.pi*sim.x/sim.x[-1])**2)
    return dict(top_gate_voltage_V=gate,bottom_gate_voltage_V=0.) if dielectric else dict(gate_voltage_V=gate)


@pytest.mark.parametrize('bad',[0.,-1.,np.nan,np.inf,True,'1',1j,[1,2],[[1],[2]],np.ones((2,2,1)),[[1,1],[1,0]],5e-324])
def test_invalid_contact_resistance(bad):
    with pytest.raises(ValueError):device(resistance=bad)


@pytest.mark.parametrize('kind,dielectric,scheme',itertools.product(('graphene','mos2'),(False,True),('midpoint','diffusion_enhanced')))
def test_small_signal_matches_independent_series_network(kind,dielectric,scheme):
    material=graphene_sheet() if kind=='graphene' else mos2_sheet(reference_eV=-.9)
    st=material.statistics();density=np.array([float(st.n_m2),float(st.p_m2)])
    length=200e-9;width=100e-9
    channel_rho=length/(Q*np.array([.02,.01])*density)
    resistance=np.array([.3*channel_rho,.7*channel_rho])
    sim=device(kind,dielectric,scheme,resistance)
    results=[sim.solve(**drive(sim,dielectric,0.),drain_voltage_V=v,max_iter=120,tolerance=1e-13) for v in (-1e-5,1e-5)]
    for r in results:ledgers(r)
    slope=(results[1]['terminal_currents_into_sheet_A']['drain']-results[0]['terminal_currents_into_sheet_A']['drain'])/2e-5
    expected=np.sum(width/(channel_rho+resistance.sum(axis=0)))
    assert abs(slope/expected-1)<1e-6


@pytest.mark.parametrize('kind,dielectric,scheme,bias',itertools.product(('graphene','mos2'),(False,True),('midpoint','diffusion_enhanced'),(-.02,0.,.02)))
def test_conservative_contacts_and_power(kind,dielectric,scheme,bias):
    resistance=np.array([[.003,.007],[.011,.005]])
    sim=device(kind,dielectric,scheme,resistance)
    r=sim.solve(**drive(sim,dielectric),drain_voltage_V=bias,max_iter=120,tolerance=1e-12)
    ledgers(r)
    assert r['contact_model']=='linear_electrochemical_edge'
    expected=sim._widths(sim.y)[None,None,:]/resistance[:,:,None]*r['contact_fermi_drop_eV']
    np.testing.assert_array_equal(r['contact_currents_into_sheet_A'],expected)
    assert r['contact_dissipation_W']>=0 and r['sheet_dissipation_W']>=0
    assert r['dissipation_W']==r['sheet_dissipation_W']+r['contact_dissipation_W']
    for a,name in enumerate(('source','drain')):
        metal=r['terminal_currents_into_sheet_A'][name]
        assert abs(metal-r['contact_currents_into_sheet_A'][a].sum())<1e-20
        assert abs(metal-r['sheet_terminal_currents_into_sheet_A'][name])<1e-8*max(abs(metal),1e-17)
    if bias:
        assert r['contact_dissipation_W']>0
        assert np.max(abs(r['contact_fermi_drop_eV']))>1e-5
    else:assert np.max(abs(r['contact_currents_into_sheet_A']))==0.


@pytest.mark.parametrize('kind,dielectric',itertools.product(('graphene','mos2'),(False,True)))
def test_full_contact_jacobian(kind,dielectric):
    sim=device(kind,dielectric,resistance=[[.003,.007],[.011,.005]],nx=5)
    N=sim.size;rng=np.random.default_rng(502);u=rng.normal(0,.025,3*N);d=rng.normal(0,1,3*N)
    gate=sim.dielectric.gate_drive(top_gate_voltage_V=-.1,bottom_gate_voltage_V=0.) if dielectric else np.full(N,-.1)
    bc=(np.zeros(len(sim.contacts)),)*3
    _,scale,J,*_=sim._evaluate(u,gate,bc);h=2e-7
    fd=(sim._evaluate(u+h*d,gate,bc,False)[0]-sim._evaluate(u-h*d,gate,bc,False)[0])/(2*h)
    assert np.max(abs((J@d-fd)/scale))<2e-5


@pytest.mark.parametrize('kind,dielectric',itertools.product(('graphene','mos2'),(False,True)))
def test_width_scaling_includes_contacts(kind,dielectric):
    results=[]
    for width in (100e-9,300e-9):
        sim=device(kind,dielectric,width=width)
        r=sim.solve(**drive(sim,dielectric,0.),drain_voltage_V=.02,max_iter=120,tolerance=1e-12)
        ledgers(r);results.append(r)
    np.testing.assert_allclose(results[1]['Fn_eV'],results[0]['Fn_eV'],rtol=1e-8,atol=1e-11)
    assert abs(results[1]['terminal_currents_into_sheet_A']['drain']/results[0]['terminal_currents_into_sheet_A']['drain']-3)<1e-8


@pytest.mark.parametrize('dielectric',(False,True))
def test_stopped_iterate_reports_metal_injection_and_keeps_input(dielectric,monkeypatch):
    sim=device(dielectric=dielectric)
    initial={key:np.full(sim.shape,value) for key,value in [('phi_V',.03),('Fn_eV',.01),('Fp_eV',-.01)]}
    saved={k:v.copy() for k,v in initial.items()}
    first=[];original=sim._evaluate
    def capture(u,*args,**kwargs):
        if not first:first.append(u.copy())
        return original(u,*args,**kwargs)
    monkeypatch.setattr(sim,'_evaluate',capture)
    r=sim.solve(**drive(sim,dielectric,amplitude=-.3),drain_voltage_V=.08,initial=initial,max_iter=1,tolerance=1e-14)
    assert not r['converged']
    for k in initial:np.testing.assert_array_equal(initial[k],saved[k])
    injection=r['contact_currents_into_sheet_A']
    for a,name in enumerate(('source','drain')):assert abs(injection[a].sum()-r['terminal_currents_into_sheet_A'][name])<1e-18
    assert r['residual_scaled_linf']>1e-14
    for block,key in ((1,'Fn_eV'),(2,'Fp_eV')):
        np.testing.assert_array_equal(first[0].reshape(3,sim.size)[block,sim.contacts],saved[key].ravel()[sim.contacts])


def test_contact_parameters_owned_and_results_independent():
    resistance=np.full((2,2),.003);sim=device(resistance=resistance)
    resistance[:]=1.
    np.testing.assert_array_equal(sim.contact_resistance_ohm_m,.003)
    assert not sim.contact_resistance_ohm_m.flags.writeable
    r=sim.solve(**drive(sim,False),drain_voltage_V=.02)
    r['contact_resistance_ohm_m'][:]=2.
    np.testing.assert_array_equal(sim.contact_resistance_ohm_m,.003)
