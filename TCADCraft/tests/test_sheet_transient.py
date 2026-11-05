"""Sheet carrier storage, electrode charge differences, and RC dynamics."""
import copy
import itertools

import numpy as np
import pytest
from scipy.linalg import expm

from tcad.material import graphene_sheet, mos2_sheet
from tcad.material.sheet import Q, KB, HBAR
from tcad.solver.sheet_drift_diffusion import SheetDriftDiffusion
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion
from tcad.solver.sheet_transient import SheetTransient


CASES=list(itertools.product(('ideal','linear','thermionic','dirac'),(False,True),('midpoint','diffusion_enhanced')))


def device(contact='linear',dielectric=False,scheme='midpoint'):
    material=mos2_sheet(reference_eV=-.9) if contact=='thermionic' else graphene_sheet()
    x=np.array([0.,.15,.5,.85,1.])*200e-9;y=np.array([0.,.4,1.])*100e-9
    common=dict(mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,transport_scheme=scheme)
    if contact=='linear':common['contact_resistance_ohm_m']=.003
    if contact=='thermionic':common['thermionic_barrier_n_eV']=.12
    if contact=='dirac':common['dirac_contact_offset_eV']=(-.02,.03)
    if dielectric:
        return DielectricSheetDriftDiffusion(x,y,np.linspace(-10e-9,10e-9,5),material,
            sheet_index=2,permittivity_F_m=5*8.8541878128e-12,**common)
    return SheetDriftDiffusion(x,y,material,gate_capacitance_F_m2=.006,**common)


def gate(dielectric,value):
    return dict(top_gate_voltage_V=value,bottom_gate_voltage_V=0.) if dielectric else dict(gate_voltage_V=value)


def check_step(sim,old,r,dt):
    assert r['converged'] and r['accepted']
    rate=np.array([-Q*sim.area*(r['n_m2'].ravel()-old['n_m2'].ravel())/dt,
                    Q*sim.area*(r['p_m2'].ravel()-old['p_m2'].ravel())/dt])
    np.testing.assert_array_equal(rate.reshape((2,)+sim.shape),r['carrier_charge_rate_C_s'])
    # Reassemble FV continuity directly from the exported physical edge flows.
    div=np.zeros_like(rate)
    for (i,j),flow in zip(r['edge_nodes'],r['edge_currents_A']):
        div[:,i]+=flow;div[:,j]-=flow
    injection=np.zeros_like(rate)
    if sim._has_finite_contacts:
        for a,nodes in enumerate((sim.left,sim.right)):
            injection[:,nodes]=r['contact_currents_into_sheet_A'][a]
    else:
        injection[:,sim.contacts]=(div+rate)[:,sim.contacts]
    scale=max(np.max(abs(div)),np.max(abs(rate)),np.max(abs(injection)),1e-20)
    assert np.max(abs(rate+div-injection))<1e-8*scale+1e-20
    for a,(name,nodes) in enumerate((('source',sim.left),('drain',sim.right))):
        assert abs(r['terminal_currents_into_sheet_A'][name]-injection[:,nodes].sum())<1e-18
        expected=(r['contact_charge_C'][name]-old['contact_charge_C'][name])/dt
        assert r['contact_displacement_currents_A'][name]==expected
    for name,current in r['gate_displacement_currents_A'].items():
        assert current==(r[name+'_charge_C']-old[name+'_charge_C'])/dt
    assert abs(r['terminal_current_sum_A']-rate.sum())<1e-8*scale+1e-20
    assert abs(r['terminal_total_current_sum_A'])<1e-8*scale+1e-20
    qscale=max(abs(r['sheet_charge_C']),abs(old['sheet_charge_C']),1e-30)/dt
    assert abs((r['sheet_charge_C']-old['sheet_charge_C'])/dt-rate.sum())<2e-12*qscale+1e-20


@pytest.mark.parametrize('contact,dielectric,scheme',CASES)
def test_pulse_conserves_carriers_and_all_terminal_currents(contact,dielectric,scheme):
    sim=device(contact,dielectric,scheme)
    tr=SheetTransient(sim,initial_drive=gate(dielectric,0.),tolerance=1e-12,max_iter=120)
    observed=False
    for k,(vg,vd) in enumerate(((.015,.005),(-.01,-.003),(0.,0.))):
        old=tr.state;dt=2e-12
        r=tr.step(dt_s=dt,**gate(dielectric,vg),drain_voltage_V=vd,tolerance=1e-12,max_iter=120)
        check_step(sim,old,r,dt)
        assert r['time_s']==tr.time_s and tr.time_s==(k+1)*dt
        observed|=abs(r['terminal_current_sum_A'])>1e-12
        assert r['dissipation_W']>=0
    assert observed  # A static DC sweep would fail this assertion.


@pytest.mark.parametrize('contact,dielectric,scheme',CASES)
def test_storage_full_jacobian(contact,dielectric,scheme):
    sim=device(contact,dielectric,scheme);N=sim.size
    rng=np.random.default_rng(505);u=rng.normal(0,.01,3*N);direction=rng.normal(size=3*N)
    old=sim.material.statistics(.003,.001,-.001)
    sim._transient_storage=(np.full(N,old.n_m2),np.full(N,old.p_m2),3e-12)
    drive=sim.dielectric.gate_drive(top_gate_voltage_V=.02,bottom_gate_voltage_V=0.) if dielectric else np.full(N,.02)
    bc=(np.zeros(len(sim.contacts)),)*3
    _,scale,J,*_=sim._evaluate(u,drive,bc);h=1e-7
    fd=(sim._evaluate(u+h*direction,drive,bc,False)[0]-sim._evaluate(u-h*direction,drive,bc,False)[0])/(2*h)
    assert np.max(abs((J@direction-fd)/scale))<2e-5


def linear_rc_network(sim):
    """Analytical neutral Dirac DOS + resistor/capacitor network, no DD Jacobian."""
    T=300.;vf=1e6;g=4.;cap=.006;N=sim.size;vt=KB*T/Q
    pref=g*(KB*T)**2/(2*np.pi*HBAR**2*vf**2)
    density=pref*np.pi**2/12;derivative=pref*np.log(2)/vt
    M=np.zeros((2*N,2*N));K=np.zeros_like(M);B=np.zeros(2*N)
    contacts=set(sim.contacts.tolist())
    for i in range(N):
        m=Q*sim.area[i]*derivative
        a=0. if i in contacts else Q*derivative/(cap+2*Q*derivative)
        b=0. if i in contacts else cap/(cap+2*Q*derivative)
        for s in range(2):
            M[s*N+i,s*N+i]+=m
            for t in range(2):M[s*N+i,t*N+i]-=m*a
            B[s*N+i]=m*b
    for s,mu in enumerate((.02,.01)):
        for i,j,geometry,*_ in sim.edges:
            G=Q*mu*density*geometry;i+=s*N;j+=s*N
            K[i,i]+=G;K[j,j]+=G;K[i,j]-=G;K[j,i]-=G
        for nodes in (sim.left,sim.right):
            for i,w in zip(nodes,sim._widths(sim.y)):K[s*N+i,s*N+i]+=w/.003
    return M,K,B


@pytest.mark.parametrize('scheme',('midpoint','diffusion_enhanced'))
def test_independent_linear_rc_and_first_order_time_refinement(scheme):
    sim=device(scheme=scheme);M,K,B=linear_rc_network(sim)
    amplitude=2e-6;end=20e-12
    jump=-np.linalg.solve(M,B)*amplitude
    exact=expm(-np.linalg.solve(M,K)*end)@jump
    errors=[]
    for count in (8,16,32):
        tr=SheetTransient(sim,initial_drive=gate(False,0.),tolerance=1e-13)
        dt=end/count;linear=np.zeros(2*sim.size)
        for k in range(count):
            linear=np.linalg.solve(M+dt*K,M@linear-(B*amplitude if k==0 else 0.))
            r=tr.step(dt_s=dt,gate_voltage_V=amplitude,tolerance=1e-13)
            assert r['accepted']
            actual=np.r_[r['Fn_eV'].ravel(),r['Fp_eV'].ravel()]
            assert np.max(abs(actual-linear))<2e-4*amplitude
        errors.append(np.max(abs(actual-exact)))
    assert errors[1]/errors[0]<.65 and errors[2]/errors[1]<.65
    assert errors[-1]<.015*amplitude


@pytest.mark.parametrize('dielectric',(False,True))
def test_failed_step_and_exception_keep_accepted_state_and_allow_retry(dielectric,monkeypatch):
    sim=device(dielectric=dielectric);tr=SheetTransient(sim,initial_drive=gate(dielectric,0.))
    before=tr.state
    r=tr.step(dt_s=2e-12,**gate(dielectric,.3),max_iter=1,tolerance=1e-14)
    assert not r['accepted'] and r['time_s']==0. and r['proposed_time_s']==2e-12
    assert tr.time_s==0.
    np.testing.assert_array_equal(before['n_m2'],tr.state['n_m2'])
    method=type(sim)._charge_ledger
    def fail(*args,**kwargs):raise MemoryError('injected ledger allocation failure')
    monkeypatch.setattr(type(sim),'_charge_ledger',fail)
    with pytest.raises(MemoryError):tr.step(dt_s=2e-12,**gate(dielectric,.02))
    np.testing.assert_array_equal(before['phi_V'],tr.state['phi_V']);assert tr.time_s==0.
    monkeypatch.setattr(type(sim),'_charge_ledger',method)
    clean=SheetTransient(sim,initial_drive=gate(dielectric,0.))
    a=tr.step(dt_s=2e-12,**gate(dielectric,.02));b=clean.step(dt_s=2e-12,**gate(dielectric,.02))
    for key in ('phi_V','Fn_eV','Fp_eV','edge_currents_A'):np.testing.assert_array_equal(a[key],b[key])


@pytest.mark.parametrize('dielectric',(False,True))
def test_private_device_drive_and_result_ownership(dielectric):
    sim=device(dielectric=dielectric);drive=gate(dielectric,np.zeros(sim.shape))
    tr=SheetTransient(sim,initial_drive=drive);clean=SheetTransient(sim,initial_drive=copy.deepcopy(drive))
    for v in drive.values():
        if isinstance(v,np.ndarray):v[:]=99.
    sim.mu_n=99.;sim.contact_resistance_ohm_m.setflags(write=True);sim.contact_resistance_ohm_m[:]=99.
    exported=tr.state;exported['n_m2'][:]=0.;exported['contact_charge_C']['source']=99.
    r=tr.step(dt_s=2e-12,**gate(dielectric,.01));ref=clean.step(dt_s=2e-12,**gate(dielectric,.01))
    np.testing.assert_array_equal(r['phi_V'],ref['phi_V'])
    saved=tr.state;r['Fn_eV'][:]=99.;r['terminal_total_currents_A']['source']=99.
    np.testing.assert_array_equal(saved['Fn_eV'],tr.state['Fn_eV'])
    assert tr.state['terminal_total_currents_A']['source']!=99.


@pytest.mark.parametrize('bad',[0.,-1.,np.nan,np.inf,True,'1',1j,[1.],5e-324])
def test_invalid_dt_does_not_commit(bad):
    tr=SheetTransient(device(),initial_drive=gate(False,0.))
    with pytest.raises((ValueError,FloatingPointError)):tr.step(dt_s=bad,gate_voltage_V=.01)
    assert tr.time_s==0.


@pytest.mark.parametrize('bad',[{'initial':{}},{'fermi_offset_eV':.1},{'temperature_K':350.},{'top_gate_voltage_V':1.}])
def test_invalid_step_drive_does_not_commit(bad):
    tr=SheetTransient(device(),initial_drive=gate(False,0.))
    with pytest.raises(ValueError):tr.step(dt_s=1e-12,**bad)
    assert tr.time_s==0.


@pytest.mark.parametrize('bad',[{},[],{'gate_voltage_V':0.,'initial':{}},{'gate_voltage_V':np.nan}])
def test_invalid_initial_drive(bad):
    with pytest.raises(ValueError):SheetTransient(device(),initial_drive=bad)


def test_unconverged_initialization_rejected():
    with pytest.raises(ValueError,match='initial DC'):
        SheetTransient(device(),initial_drive=gate(False,.3),max_iter=1,tolerance=1e-14)


def test_unsupported_device_rejected():
    with pytest.raises(TypeError):SheetTransient(object(),initial_drive=gate(False,0.))
