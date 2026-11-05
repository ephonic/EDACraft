"""Four-rate sheet trap kinetics and self-consistent charge transfer."""
import copy
import itertools
import mpmath as mp
import numpy as np
import pytest

from tcad.material.sheet import Q
from tcad.solver.sheet_traps import SheetTrap
from tcad.solver.sheet_transient import SheetTransient
from test_sheet_transient import device,gate,CASES


def traps(kind='acceptor',density=1e14):
    return SheetTrap(density,2e-6,1e-6,2e9,3e8,kind)


@pytest.mark.parametrize('f0,dt,n,p',itertools.product((0.,.3,1.),(1e-18,3e-11,1.),(1e12,1e16),(2e12,)))
def test_eliminated_occupancy_and_rates_match_80_digit_reference(f0,dt,n,p):
    model=traps();r=model.evaluate(n,p,f0,dt)
    with mp.workdps(80):
        cn=mp.mpf('2e-6');cp=mp.mpf('1e-6');en=mp.mpf('2e9');ep=mp.mpf('3e8')
        a=cn*n+ep;b=en+cp*p;h=1/mp.mpf(str(dt));f=(h*mp.mpf(str(f0))+a)/(h+a+b)
        rn=cn*n*(1-f)-en*f;rp=cp*p*f-ep*(1-f)
        for name,expected in (('occupancy',f),('electron_capture_s',rn),('hole_capture_s',rp)):
            assert abs(float(r[name])-float(expected))<2e-14*max(1.,abs(float(expected)))
    assert 0<=r['occupancy']<=1
    assert abs((r['occupancy']-f0)/dt-(r['electron_capture_s']-r['hole_capture_s']))<1e-7*max(float(a+b),1.)


@pytest.mark.parametrize('coefficients',[(2e-6,0.,2e9,0.),(0.,1e-6,0.,3e8),(2e-6,1e-6,2e9,3e8)])
def test_constant_reservoir_analytic_relaxation_and_time_refinement(coefficients):
    model=SheetTrap(1e14,*coefficients);cn,cp,en,ep=coefficients;n=1e15;p=2e14
    a=cn*n+ep;b=en+cp*p;lam=a+b;end=3/lam;equilibrium=a/lam;initial=.2
    exact=equilibrium+(initial-equilibrium)*np.exp(-lam*end);errors=[]
    for count in (8,16,32):
        f=initial;dt=end/count
        for k in range(count):f=float(model.evaluate(n,p,f,dt)['occupancy'])
        discrete=equilibrium+(initial-equilibrium)/(1+lam*dt)**count
        assert abs(f-discrete)<2e-15
        errors.append(abs(f-exact))
    assert errors[1]/errors[0]<.65 and errors[2]/errors[1]<.65


@pytest.mark.parametrize('kind',('acceptor','donor'))
def test_frozen_rates_and_charge_convention(kind):
    model=SheetTrap(2e14,0.,0.,0.,0.,kind)
    r=model.evaluate(1e15,2e14,.3,1e-9)
    assert r['occupancy']==.3 and r['electron_capture_s']==r['hole_capture_s']==0.
    assert abs(r['charge_C_m2']-Q*2e14*((1 if kind=='donor' else 0)-.3))<1e-20


@pytest.mark.parametrize('contact,dielectric,scheme',CASES)
def test_self_consistent_capture_conserves_free_trapped_and_terminal_charge(contact,dielectric,scheme):
    sim=device(contact,dielectric,scheme);model=traps('donor' if scheme=='midpoint' else 'acceptor')
    run=SheetTransient(sim,initial_drive=gate(dielectric,0.),traps=model,initial_occupancy=.2,max_iter=120,tolerance=1e-12)
    assert not run.state['trap_rates_active']
    for vg,vd in ((.025,.005),(-.015,-.003),(0.,0.)):
        old=run.state;dt=5e-12
        r=run.step(dt_s=dt,**gate(dielectric,vg),drain_voltage_V=vd,max_iter=120,tolerance=1e-12)
        assert r['accepted'] and r['trap_rates_active']
        f=np.array(r['trap_occupancy']).ravel();f0=np.array(old['trap_occupancy']).ravel()
        rn=r['trap_electron_capture_s'].ravel();rp=r['trap_hole_capture_s'].ravel()
        assert np.all((f>=0)&(f<=1))
        assert np.max(abs(f-f0))>1e-4
        assert np.max(abs((f-f0)/dt-rn+rp))<1e-3
        free=np.array(r['carrier_charge_rate_C_s']).reshape(2,-1)
        trap_rate=-Q*sim.area*1e14*(f-f0)/dt
        np.testing.assert_array_equal(trap_rate,r['trap_charge_rate_C_s'].ravel())
        div=np.zeros_like(free)
        for (i,j),flow in zip(r['edge_nodes'],r['edge_currents_A']):div[:,i]+=flow;div[:,j]-=flow
        sources=Q*sim.area*1e14*np.array([rn,-rp]);injection=np.zeros_like(free)
        if sim._has_finite_contacts:
            for a,nodes in enumerate((sim.left,sim.right)):injection[:,nodes]=r['contact_currents_into_sheet_A'][a]
        else:injection[:,sim.contacts]=(free+div-sources)[:,sim.contacts]
        scale=max(np.max(abs(free)),np.max(abs(div)),np.max(abs(sources)),np.max(abs(injection)),1e-20)
        assert np.max(abs(free+div-injection-sources))<1e-8*scale+1e-20
        for name,nodes in (('source',sim.left),('drain',sim.right)):
            assert abs(r['terminal_currents_into_sheet_A'][name]-injection[:,nodes].sum())<1e-8*scale+1e-20
        expected=free.sum()+trap_rate.sum()
        assert abs(r['sheet_charge_rate_A']-expected)<1e-12*scale+1e-20
        assert abs(r['terminal_current_sum_A']-expected)<1e-8*scale+1e-20
        assert abs(r['terminal_total_current_sum_A'])<1e-8*scale+1e-20
        qscale=max(abs(r['sheet_charge_C']),abs(old['sheet_charge_C']),1e-30)/dt
        assert abs((r['sheet_charge_C']-old['sheet_charge_C'])/dt-expected)<1e-10*qscale+1e-20
        charge=Q*1e14*((1 if model.kind=='donor' else 0)-f)
        np.testing.assert_array_equal(r['trap_charge_C_m2'].ravel(),charge)
        assert abs(r['trap_charge_C']-np.dot(sim.area,charge))<1e-30


@pytest.mark.parametrize('contact,dielectric,scheme',CASES)
def test_full_eliminated_trap_jacobian(contact,dielectric,scheme):
    sim=device(contact,dielectric,scheme);N=sim.size;rng=np.random.default_rng(506)
    sim._sheet_trap=(traps().bind(sim.shape),np.full(N,.3),3e-12)
    previous=sim.material.statistics(.002,0.,0.)
    sim._transient_storage=(np.full(N,previous.n_m2),np.full(N,previous.p_m2),3e-12)
    u=rng.normal(0,.01,3*N);d=rng.normal(size=3*N)
    vg=sim.dielectric.gate_drive(top_gate_voltage_V=.02,bottom_gate_voltage_V=0.) if dielectric else np.full(N,.02)
    bc=(np.zeros(len(sim.contacts)),)*3
    _,scale,J,*_=sim._evaluate(u,vg,bc);h=1e-7
    fd=(sim._evaluate(u+h*d,vg,bc,False)[0]-sim._evaluate(u-h*d,vg,bc,False)[0])/(2*h)
    assert np.max(abs((J@d-fd)/scale))<2e-5


@pytest.mark.parametrize('dielectric',(False,True))
def test_zero_density_preserves_parent_carrier_transient(dielectric):
    sim=device(dielectric=dielectric)
    plain=SheetTransient(sim,initial_drive=gate(dielectric,0.))
    trapped=SheetTransient(sim,initial_drive=gate(dielectric,0.),traps=traps(density=0.),initial_occupancy=.2)
    for v in (.02,0.):
        a=plain.step(dt_s=5e-12,**gate(dielectric,v));b=trapped.step(dt_s=5e-12,**gate(dielectric,v))
        assert a['accepted'] and b['accepted']
        for key in ('phi_V','Fn_eV','Fp_eV','n_m2','p_m2','edge_currents_A'):
            np.testing.assert_array_equal(a[key],b[key])


@pytest.mark.parametrize('dielectric',(False,True))
def test_failure_exception_retry_and_history_ownership(dielectric,monkeypatch):
    sim=device(dielectric=dielectric);density=np.full(sim.shape,1e14);f0=np.full(sim.shape,.2)
    model=traps(density=density);args=dict(initial_drive=gate(dielectric,0.),traps=model,initial_occupancy=f0)
    run=SheetTransient(sim,**args);clean=SheetTransient(sim,**args);before=run.state
    density[:]=0.;f0[:]=0.;export=run.state;export['trap_occupancy'][:]=1.
    r=run.step(dt_s=1e-10,**gate(dielectric,.3),max_iter=1,tolerance=1e-14)
    assert not r['accepted'] and run.time_s==0.
    np.testing.assert_array_equal(before['trap_occupancy'],run.state['trap_occupancy'])
    original=SheetTrap.evaluate
    def fail(*args,**kwargs):raise MemoryError('trap allocation probe')
    monkeypatch.setattr(SheetTrap,'evaluate',fail)
    with pytest.raises(MemoryError):run.step(dt_s=5e-12,**gate(dielectric,.02))
    assert run.time_s==0.
    monkeypatch.setattr(SheetTrap,'evaluate',original)
    a=run.step(dt_s=5e-12,**gate(dielectric,.02));b=clean.step(dt_s=5e-12,**gate(dielectric,.02))
    for k in ('trap_occupancy','phi_V','Fn_eV','Fp_eV','trap_charge_rate_C_s'):np.testing.assert_array_equal(a[k],b[k])
    saved=run.state;a['trap_occupancy'][:]=0.
    np.testing.assert_array_equal(saved['trap_occupancy'],run.state['trap_occupancy'])


@pytest.mark.parametrize('name',('density_m2','capture_n_m2_s','capture_p_m2_s','emission_n_s','emission_p_s'))
@pytest.mark.parametrize('bad',(-1.,np.inf,True,1j))
def test_invalid_trap_parameters(name,bad):
    kw=dict(density_m2=1e14,capture_n_m2_s=1e-6,capture_p_m2_s=0.,emission_n_s=1e9,emission_p_s=0.)
    kw[name]=bad
    with pytest.raises(ValueError):SheetTrap(**kw)


@pytest.mark.parametrize('bad',(-.1,1.1,np.nan,True,[0.,1.]))
def test_invalid_initial_occupancy(bad):
    with pytest.raises(ValueError):SheetTransient(device(),initial_drive=gate(False,0.),traps=traps(),initial_occupancy=bad)


def test_missing_or_unmatched_trap_initialization_rejected():
    for kwargs in ({'traps':traps()},{'initial_occupancy':.2}):
        with pytest.raises(ValueError):SheetTransient(device(),initial_drive=gate(False,0.),**kwargs)
    with pytest.raises(ValueError):SheetTrap(1e14,0.,0.,0.,0.,kind='both')


@pytest.mark.parametrize('contact',('linear','thermionic'))
def test_coupled_device_fixed_waveform_time_refinement(contact):
    sim=device(contact,False,'diffusion_enhanced');end=80e-12;states=[]
    for count in (8,16,32,64):
        run=SheetTransient(sim,initial_drive=gate(False,0.),traps=traps(),initial_occupancy=.2,tolerance=1e-12,max_iter=120)
        for k in range(count):
            r=run.step(dt_s=end/count,gate_voltage_V=.025,drain_voltage_V=.003,tolerance=1e-12,max_iter=120)
            assert r['accepted']
        states.append(np.r_[r['trap_occupancy'].ravel(),r['phi_V'].ravel()/.025,
                            r['Fn_eV'].ravel()/.025,r['Fp_eV'].ravel()/.025])
    diffs=[np.max(abs(b-a)) for a,b in zip(states,states[1:])]
    assert diffs[1]/diffs[0]<.7 and diffs[2]/diffs[1]<.7
    assert diffs[-1]<.01
