"""Self-consistent thermal initialization and release to kinetic history."""
import itertools
import mpmath as mp
import numpy as np
import pytest
from tcad.material.sheet import KB,Q,mos2_sheet,graphene_sheet
from tcad.solver.sheet_trap_balance import EnergySheetTrap
from tcad.solver.sheet_traps import SheetTrap
from tcad.solver.sheet_transient import SheetTransient
from test_sheet_transient import device,gate,CASES
from test_sheet_trap_balance import GRID

THERMAL_CASES=[(*case,kind) for case in CASES for kind in ('acceptor','donor')]


def model_for(sim,kind='acceptor'):
    yy,xx=np.meshgrid(np.linspace(0.,1.,len(sim.y)),np.linspace(0.,1.,len(sim.x)),indexing='ij')
    offset=sim.material.gap_eV/2-.04 if sim.material.dispersion=='parabolic' else .01
    return EnergySheetTrap(1e14*(1+.2*xx+.1*yy),2e-6,1e-6,
        offset+.003*(xx-yy),1.5+.3*yy,kind)


def initial_drive(sim,dielectric):
    y,x=np.meshgrid(np.linspace(0.,1.,len(sim.y)),np.linspace(0.,1.,len(sim.x)),indexing='ij')
    return dict(**gate(dielectric,.015+.01*x*y),source_voltage_V=.01,
        drain_voltage_V=.01,fermi_offset_eV=.004)


@pytest.mark.parametrize('dispersion,T,eta,g,kind',[(*case,kind) for case in GRID for kind in ('acceptor','donor')])
def test_thermal_occupancy_and_potential_derivative_match_80_digits(dispersion,T,eta,g,kind):
    material=mos2_sheet() if dispersion=='parabolic' else graphene_sheet()
    vt=KB*T/Q;F=material.reference_eV+material.gap_eV/2+eta*vt
    offset=material.gap_eV/2-.04 if dispersion=='parabolic' else .01
    model=EnergySheetTrap(1e14,2e-6,1e-6,offset,g,kind);phi=.003
    r=model.evaluate(material,phi,F,F,T,None,equilibrium_fermi_eV=F)
    with mp.workdps(80):
        v=mp.mpf('1.380649e-23')*mp.mpf(T)/mp.mpf('1.602176634e-19')
        z=(mp.mpf(F)+mp.mpf(phi)-mp.mpf(material.reference_eV)-mp.mpf(offset))/v+mp.log(mp.mpf(g))
        f=1/(1+mp.exp(-z));empty=1/(1+mp.exp(z));deriv=f*empty/v
        charge=mp.mpf('1.602176634e-19')*mp.mpf(1e14)*((1 if kind=='donor' else 0)-f)
        for name,expected in (('occupancy',f),('empty',empty),('df_dphi',deriv),('charge_C_m2',charge)):
            assert abs(float(r[name])-float(expected))<1e-12*max(abs(float(expected)),1e-100)
    assert r['df_dFn']==r['df_dFp']==0.
    h=1e-7
    def value(v):return model.evaluate(material,v,F,F,T,None,equilibrium_fermi_eV=F)['occupancy']
    # Scale with f*(1-f), since an almost full trap cannot resolve relative
    # differences of f itself to arbitrarily small finite-difference steps.
    fd=(value(phi+h)-value(phi-h))/(2*h)
    assert abs(fd-r['df_dphi'])<1e-8*max(float(r['df_dphi']),1.)


@pytest.mark.parametrize('contact,dielectric,scheme,kind',THERMAL_CASES)
def test_full_equilibrium_poisson_jacobian(contact,dielectric,scheme,kind):
    sim=device(contact,dielectric,scheme);N=sim.size;rng=np.random.default_rng(508)
    sim._sheet_trap=(model_for(sim,kind).bind(sim.shape),None,None)
    sim._sheet_equilibrium_fermi_eV=-.006
    u=rng.normal(0,.01,3*N);direction=rng.normal(size=3*N)
    vg=sim.dielectric.gate_drive(top_gate_voltage_V=.02,bottom_gate_voltage_V=0.) if dielectric else np.full(N,.02)
    bc=(np.zeros(len(sim.contacts)),)*3
    _,scale,J,*_=sim._evaluate(u,vg,bc);h=1e-7
    fd=(sim._evaluate(u+h*direction,vg,bc,False)[0]-sim._evaluate(u-h*direction,vg,bc,False)[0])/(2*h)
    assert np.max(abs((J@direction-fd)/scale))<2e-5


@pytest.mark.parametrize('contact,dielectric,scheme,kind',THERMAL_CASES)
def test_self_consistent_initialization_stationary_hold_and_release(contact,dielectric,scheme,kind):
    sim=device(contact,dielectric,scheme);model=model_for(sim,kind)
    run=SheetTransient(sim,initial_drive=initial_drive(sim,dielectric),traps=model,
        initial_occupancy='equilibrium',tolerance=1e-12,max_iter=120)
    r=run.state;initial=r;vt=KB*sim.temperature_K/Q;F=-.006
    assert r['trap_initialization']=='thermal_equilibrium' and r['trap_equilibrium_fermi_eV']==F
    expected=1/(1+np.exp((sim.material.reference_eV+model.energy_offset_eV-r['phi_V']-F)/vt)/model.degeneracy)
    np.testing.assert_allclose(r['trap_occupancy'],expected,rtol=0,atol=2e-15)
    for key in ('Fn_eV','Fp_eV'):np.testing.assert_allclose(r[key],F,rtol=0,atol=1e-14)
    assert np.ptp(r['trap_occupancy'])>1e-4
    for dt in (5e-12,50e-12):
        r=run.step(dt_s=dt,tolerance=1e-12,max_iter=120)
        assert r['accepted']
        np.testing.assert_allclose(r['trap_occupancy'],initial['trap_occupancy'],rtol=0,atol=1e-13)
        for k in ('phi_V','Fn_eV','Fp_eV'):np.testing.assert_allclose(r[k],initial[k],rtol=0,atol=1e-12)
        assert max(abs(v) for v in r['terminal_total_currents_A'].values())<1e-16
    before=run.state
    r=run.step(dt_s=5e-12,**gate(dielectric,.045),drain_voltage_V=.015,tolerance=1e-12,max_iter=120)
    assert r['accepted'] and np.max(abs(r['trap_occupancy']-before['trap_occupancy']))>1e-5
    expected=model.bind(sim.shape).evaluate(sim.material,r['phi_V'].ravel(),r['Fn_eV'].ravel(),r['Fp_eV'].ravel(),
        sim.temperature_K,before['trap_occupancy'].ravel(),5e-12)
    np.testing.assert_array_equal(r['trap_occupancy'].ravel(),expected['occupancy'])
    equilibrium=1/(1+np.exp((sim.material.reference_eV+model.energy_offset_eV-r['phi_V']-F)/vt)/model.degeneracy)
    assert np.max(abs(r['trap_occupancy']-equilibrium))>1e-4


@pytest.mark.parametrize('contact,dielectric',itertools.product(('ideal','linear','thermionic','dirac'),(False,True)))
def test_voltage_reference_shift_preserves_physical_initial_state(contact,dielectric):
    sim=device(contact,dielectric,'diffusion_enhanced');a=initial_drive(sim,dielectric);b=dict(a);shift=.017
    for name in ('source_voltage_V','drain_voltage_V','gate_voltage_V','top_gate_voltage_V','bottom_gate_voltage_V'):
        if name in b:b[name]=b[name]+shift
    runs=[SheetTransient(sim,initial_drive=d,traps=model_for(sim),initial_occupancy='equilibrium',
        tolerance=1e-12,max_iter=120).state for d in (a,b)]
    np.testing.assert_allclose(runs[0]['phi_V']+shift,runs[1]['phi_V'],rtol=0,atol=2e-12)
    for key in ('n_m2','p_m2'):np.testing.assert_allclose(runs[0][key],runs[1][key],rtol=1e-10,atol=0)
    np.testing.assert_allclose(runs[0]['trap_occupancy'],runs[1]['trap_occupancy'],rtol=0,atol=1e-12)


@pytest.mark.parametrize('contact,dielectric',itertools.product(('ideal','linear','thermionic','dirac'),(False,True)))
def test_donor_acceptor_charge_changes_self_consistent_potential(contact,dielectric):
    sim=device(contact,dielectric,'diffusion_enhanced');runs=[]
    for kind in ('acceptor','donor'):
        r=SheetTransient(sim,initial_drive=initial_drive(sim,dielectric),traps=model_for(sim,kind),
            initial_occupancy='equilibrium',tolerance=1e-12,max_iter=120).state
        f=r['trap_occupancy'];charge=Q*model_for(sim,kind).density_m2*((1 if kind=='donor' else 0)-f)
        assert np.max(abs(r['trap_charge_C_m2']-charge)/(Q*model_for(sim,kind).density_m2))<1e-14
        runs.append(r)
    assert np.max(abs(runs[0]['phi_V']-runs[1]['phi_V']))>1e-5


@pytest.mark.parametrize('dielectric',(False,True))
def test_initialization_and_step_exceptions_leave_owned_history(dielectric,monkeypatch):
    sim=device(dielectric=dielectric);args=dict(initial_drive=initial_drive(sim,dielectric),traps=model_for(sim),initial_occupancy='equilibrium')
    original=EnergySheetTrap.evaluate;sentinel=MemoryError('equilibrium allocation probe')
    def fail(*a,**kw):raise sentinel
    monkeypatch.setattr(EnergySheetTrap,'evaluate',fail)
    with pytest.raises(MemoryError) as error:SheetTransient(sim,**args)
    assert error.value is sentinel and not hasattr(sim,'_sheet_trap')
    monkeypatch.setattr(EnergySheetTrap,'evaluate',original)
    run=SheetTransient(sim,**args);clean=SheetTransient(sim,**args);before=run.state
    r=run.step(dt_s=1e-10,**gate(dielectric,.3),max_iter=1,tolerance=1e-14)
    assert not r['accepted'] and run.time_s==0.
    monkeypatch.setattr(EnergySheetTrap,'evaluate',fail)
    with pytest.raises(MemoryError):run.step(dt_s=5e-12,**gate(dielectric,.03))
    monkeypatch.setattr(EnergySheetTrap,'evaluate',original)
    np.testing.assert_array_equal(run.state['trap_occupancy'],before['trap_occupancy'])
    a=run.step(dt_s=5e-12,**gate(dielectric,.03));b=clean.step(dt_s=5e-12,**gate(dielectric,.03))
    for k in ('phi_V','Fn_eV','Fp_eV','trap_occupancy'):np.testing.assert_array_equal(a[k],b[k])
    a['trap_occupancy'][:]=0.;np.testing.assert_array_equal(run.state['trap_occupancy'],b['trap_occupancy'])


@pytest.mark.parametrize('bad',[{'drain_voltage_V':.001},{'source_voltage_V':True},{'drain_voltage_V':np.nan},
    {'fermi_offset_eV':[0.]},{'source_voltage_V':np.inf},{'source_voltage_V':1j}])
def test_invalid_equilibrium_drive(bad):
    sim=device();drive=dict(gate_voltage_V=0.);drive.update(bad)
    with pytest.raises(ValueError):SheetTransient(sim,initial_drive=drive,traps=model_for(sim),initial_occupancy='equilibrium')


@pytest.mark.parametrize('bad',[
    dict(traps=None,initial_occupancy='equilibrium'),
    dict(traps=SheetTrap(1e14,0.,0.,0.,0.),initial_occupancy='equilibrium'),
    dict(traps=EnergySheetTrap(1e14,0.,0.),initial_occupancy='thermal'),
    dict(traps=EnergySheetTrap(1e14,0.,0.),initial_occupancy=None)])
def test_invalid_equilibrium_mode(bad):
    with pytest.raises(ValueError):SheetTransient(device(),initial_drive={'gate_voltage_V':0.},**bad)


@pytest.mark.parametrize('kw',[dict(old_occupancy=.2),dict(dt_s=1e-12)])
def test_equilibrium_constraint_rejects_history_or_time_step(kw):
    args=dict(material=graphene_sheet(),phi=0.,Fn=0.,Fp=0.,temperature_K=300.,old_occupancy=None,equilibrium_fermi_eV=0.)
    args.update(kw)
    with pytest.raises(ValueError):EnergySheetTrap(1e14,0.,0.).evaluate(**args)


@pytest.mark.parametrize('offset,kind',itertools.product((-100.,100.),('acceptor','donor')))
def test_saturated_equilibrium_has_finite_charge_and_derivative(offset,kind):
    model=EnergySheetTrap(1e14,0.,0.,offset,2.,kind)
    r=model.evaluate(graphene_sheet(),0.,0.,0.,300.,None,equilibrium_fermi_eV=0.)
    assert r['occupancy']==(1. if offset<0 else 0.) and r['df_dphi']==0.
    assert all(np.all(np.isfinite(v)) for v in r.values())
