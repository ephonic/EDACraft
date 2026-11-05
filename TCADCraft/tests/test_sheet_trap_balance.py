"""Energy-derived FD detailed balance and coupled sheet trap regression."""
import copy
import itertools
import mpmath as mp
import numpy as np
import pytest
from tcad.material.sheet import graphene_sheet, mos2_sheet, KB, Q
from tcad.solver.sheet_trap_balance import EnergySheetTrap
from tcad.solver.sheet_transient import SheetTransient
from test_sheet_transient import device, gate, CASES


def energy_traps(material, density=1e14):
    return EnergySheetTrap(density, 2e-6, 1e-6,
        material.gap_eV/2-.04 if material.dispersion == 'parabolic' else .01, 2.)


GRID = list(itertools.product(('parabolic','dirac'), (180.,300.,450.), (-15.,0.,8.), (.5,2.)))


@pytest.mark.parametrize('dispersion,T,eta,g', GRID)
def test_thermal_equilibrium_has_zero_each_net_capture(dispersion,T,eta,g):
    material = mos2_sheet() if dispersion == 'parabolic' else graphene_sheet()
    vt=KB*T/Q; F=material.reference_eV+material.gap_eV/2+eta*vt
    base=energy_traps(material)
    model=EnergySheetTrap(1e14,2e-6,1e-6,base.energy_offset_eV,g)
    f=1/(1+np.exp((float(model.energy_offset_eV)+material.reference_eV-F)/vt)/g)
    r=model.evaluate(material,0.,F,F,T,f,3e-11)
    assert abs(r['occupancy']-f)<2e-15
    for species in ('electron','hole'):
        assert abs(r[species+'_capture_s'])<1e-11*max(float(r[species+'_activity_s']),1e-100)


@pytest.mark.parametrize('dispersion,T,eta,g', GRID)
def test_nonequilibrium_rates_BE_and_derivatives_match_80_digit_reference(dispersion,T,eta,g):
    material=mos2_sheet() if dispersion=='parabolic' else graphene_sheet()
    vt=KB*T/Q; fn=material.reference_eV+material.gap_eV/2+eta*vt;fp=fn-.02
    base=energy_traps(material);model=EnergySheetTrap(1e14,2e-6,1e-6,base.energy_offset_eV,g)
    r=model.evaluate(material,0.,fn,fp,T,.3,7e-12)
    with mp.workdps(80):
        q=mp.mpf('1.602176634e-19');kb=mp.mpf('1.380649e-23');hb=mp.mpf('1.054571817e-34')
        v=kb*T/q;ref=mp.mpf(float(material.reference_eV));gap=mp.mpf(float(material.gap_eV))
        def reference(Fn,Fp):
            eneta=(Fn-ref-gap/2)/v;epeta=(ref-gap/2-Fp)/v
            if dispersion=='parabolic':
                pref=mp.mpf('9.1093837015e-31')*kb*T/(2*mp.pi*hb**2)
                n=pref*material.mass_n_m0*material.degeneracy_n*mp.log1p(mp.exp(eneta))
                p=pref*material.mass_p_m0*material.degeneracy_p*mp.log1p(mp.exp(epeta))
            else:
                pref=material.degeneracy_n/(2*mp.pi)*(kb*T/(hb*material.fermi_velocity_m_s))**2
                n=-pref*mp.polylog(2,-mp.exp(eneta));p=-pref*mp.polylog(2,-mp.exp(epeta))
            Et=ref+mp.mpf(float(model.energy_offset_eV));cn=mp.mpf(float(model.capture_n_m2_s));cp=mp.mpf(float(model.capture_p_m2_s))
            en=cn*n*mp.exp((Et-Fn)/v)/g;ep=cp*p*mp.exp((Fp-Et)/v)*g
            h=1/mp.mpf(7e-12);a=cn*n+ep;b=en+cp*p
            f=(h*mp.mpf(.3)+a)/(h+a+b)
            return f,cn*n*(1-f)-en*f,cp*p*f-ep*(1-f),en,ep
        a,b=mp.mpf(fn),mp.mpf(fp);expected=reference(a,b)
        for key,val in zip(('occupancy','electron_capture_s','hole_capture_s','emission_n_s','emission_p_s'),expected):
            assert abs(float(r[key])-float(val))<1e-10*max(abs(float(val)),1e-100)
        for j,prefix in enumerate(('df','drn','drp')):
            for axis,label in ((0,'Fn'),(1,'Fp')):
                deriv=mp.diff(lambda x:reference(x,b)[j],a) if axis==0 else mp.diff(lambda x:reference(a,x)[j],b)
                assert abs(float(r[prefix+'_d'+label])-float(deriv))<1e-9*max(abs(float(deriv)),1e-100)


@pytest.mark.parametrize('contact,dielectric,scheme', CASES)
def test_energy_trap_full_coupled_jacobian(contact,dielectric,scheme):
    sim=device(contact,dielectric,scheme);N=sim.size;rng=np.random.default_rng(507)
    sim._sheet_trap=(energy_traps(sim.material).bind(sim.shape),np.full(N,.3),3e-12)
    previous=sim.material.statistics(.002,0.,0.)
    sim._transient_storage=(np.full(N,previous.n_m2),np.full(N,previous.p_m2),3e-12)
    u=rng.normal(0,.01,3*N);direction=rng.normal(size=3*N)
    vg=sim.dielectric.gate_drive(top_gate_voltage_V=.02,bottom_gate_voltage_V=0.) if dielectric else np.full(N,.02)
    bc=(np.zeros(len(sim.contacts)),)*3
    _,scale,J,*_=sim._evaluate(u,vg,bc);h=1e-7
    fd=(sim._evaluate(u+h*direction,vg,bc,False)[0]-sim._evaluate(u-h*direction,vg,bc,False)[0])/(2*h)
    assert np.max(abs((J@direction-fd)/scale))<2e-5


@pytest.mark.parametrize('contact,dielectric,scheme', CASES)
def test_energy_trap_pulses_conserve_terminal_charge(contact,dielectric,scheme):
    sim=device(contact,dielectric,scheme)
    run=SheetTransient(sim,initial_drive=gate(dielectric,0.),traps=energy_traps(sim.material),initial_occupancy=.2,tolerance=1e-12,max_iter=120)
    for vg,vd in ((.025,.005),(-.015,-.003),(0.,0.)):
        old=run.state;r=run.step(dt_s=5e-12,**gate(dielectric,vg),drain_voltage_V=vd,tolerance=1e-12,max_iter=120)
        assert r['accepted']
        scale=max(abs(r['sheet_charge_rate_A']),max(abs(v) for v in r['terminal_total_currents_A'].values()),1e-20)
        assert abs(r['terminal_total_current_sum_A'])<1e-8*scale+1e-20
        defect=(r['trap_occupancy']-old['trap_occupancy'])/5e-12-r['trap_electron_capture_s']+r['trap_hole_capture_s']
        assert np.max(abs(defect))<.01


@pytest.mark.parametrize('dielectric',(False,True))
def test_energy_trap_failure_exception_retry_and_ownership(dielectric,monkeypatch):
    sim=device(dielectric=dielectric);model=energy_traps(sim.material)
    args=dict(initial_drive=gate(dielectric,0.),traps=model,initial_occupancy=.2)
    run=SheetTransient(sim,**args);clean=SheetTransient(sim,**args);old=run.state
    r=run.step(dt_s=1e-10,**gate(dielectric,.3),max_iter=1,tolerance=1e-14)
    assert not r['accepted'] and run.time_s==0.
    original=EnergySheetTrap.evaluate
    def fail(*args,**kw):raise MemoryError('energy trap allocation probe')
    monkeypatch.setattr(EnergySheetTrap,'evaluate',fail)
    with pytest.raises(MemoryError):run.step(dt_s=5e-12,**gate(dielectric,.02))
    assert run.time_s==0.
    np.testing.assert_array_equal(old['trap_occupancy'],run.state['trap_occupancy'])
    monkeypatch.setattr(EnergySheetTrap,'evaluate',original)
    a=run.step(dt_s=5e-12,**gate(dielectric,.02));b=clean.step(dt_s=5e-12,**gate(dielectric,.02))
    for k in ('phi_V','Fn_eV','Fp_eV','trap_occupancy'):np.testing.assert_array_equal(a[k],b[k])
    a['trap_occupancy'][:]=0.;np.testing.assert_array_equal(b['trap_occupancy'],run.state['trap_occupancy'])


@pytest.mark.parametrize('name,bad',[(n,v) for n in ('density_m2','capture_n_m2_s','capture_p_m2_s','degeneracy') for v in (-1.,np.inf,True,1j)]+[('degeneracy',0.),('energy_offset_eV',np.nan)])
def test_invalid_energy_parameters(name,bad):
    kw=dict(density_m2=1e14,capture_n_m2_s=2e-6,capture_p_m2_s=1e-6)
    kw[name]=bad
    with pytest.raises(ValueError):EnergySheetTrap(**kw)


@pytest.mark.parametrize('dt',(-1.,0.,True,1e-310))
def test_invalid_timestep(dt):
    material=graphene_sheet()
    with pytest.raises(ValueError):energy_traps(material).evaluate(material,0.,0.,0.,300.,.2,dt)


def test_domain_binding_and_zero_capture():
    material=graphene_sheet();model=EnergySheetTrap(1e14,0.,0.)
    r=model.evaluate(material,0.,0.,0.,300.,.3,1e-12)
    assert r['occupancy']==.3 and r['electron_capture_s']==r['hole_capture_s']==0.
    with pytest.raises(ValueError):model.evaluate(material,0.,100.,0.,300.,.3,1e-12)
    with pytest.raises(ValueError):EnergySheetTrap([1.,2.],0.,0.).bind((3,5))
    with pytest.raises(ValueError):EnergySheetTrap(1.,0.,0.,kind='both')


@pytest.mark.parametrize('material_name,dielectric,scheme',itertools.product(('graphene','mos2'),(False,True),('midpoint','diffusion_enhanced')))
def test_coupled_zero_bias_thermal_state_has_no_false_capture(material_name,dielectric,scheme):
    sim=device('linear',dielectric,scheme)
    sim.material=graphene_sheet() if material_name=='graphene' else mos2_sheet(reference_eV=-.9)
    model=energy_traps(sim.material);vt=KB*sim.temperature_K/Q
    f=1/(1+np.exp((sim.material.reference_eV+float(model.energy_offset_eV))/vt)/float(model.degeneracy))
    free=sim.material.statistics(0.,0.,0.,sim.temperature_K)
    trap=model.evaluate(sim.material,0.,0.,0.,sim.temperature_K,f)
    sim.fixed_charge=sim._field(-float(free.charge_C_m2)-float(trap['charge_C_m2']),'fixed_charge')
    run=SheetTransient(sim,initial_drive=gate(dielectric,0.),traps=model,initial_occupancy=f,tolerance=1e-12,max_iter=120)
    initial=run.state
    r=run.step(dt_s=5e-11,tolerance=1e-12,max_iter=120)
    assert r['accepted']
    np.testing.assert_allclose(r['trap_occupancy'],f,rtol=0,atol=2e-14)
    for k in ('phi_V','Fn_eV','Fp_eV'):np.testing.assert_allclose(r[k],initial[k],rtol=0,atol=1e-13)
    for value in r['terminal_total_currents_A'].values():assert abs(value)<1e-16
