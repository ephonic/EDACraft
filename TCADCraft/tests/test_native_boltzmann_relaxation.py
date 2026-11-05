from copy import deepcopy
from dataclasses import replace,FrozenInstanceError
from decimal import Decimal,localcontext
import numpy as np
import pytest
from scipy.optimize import brentq
from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw as Law
from tcad.physics.multivalley_thermionic import ThermionicValley
from tcad.solver.boltzmann_relaxation import MBRelaxationConfiguration as Config,initialize_mb_relaxation as initialize,advance_mb_relaxation as advance
from tcad.postprocess.boltzmann_relaxation import audit_mb_relaxation_step as audit
from tcad.core._bindings import native_boltzmann_relaxation_raw as raw

ONE=(ThermionicValley('one',1,.3,.3,.3),)
def config(a=0.,c=0.):
    law=Law(150.,5e24,a,0,c)
    return Config.create(1000.,1e-20,3e-13,2e-13,ONE,ONE,laws=(law,law),temperature_bounds=(250.,450.))
def initial(cfg):return initialize(cfg,[1e25,1e25],300.,[300.,400.,250.])


@pytest.mark.parametrize('impulses',[(0.,0.,0.),(2e-19,-1e-19,3e-19),(-2e-19,1e-19,-1e-19)])
def test_constant_law_matches_independent_linear_three_temperature_BE(impulses):
    cfg=config();old=initial(cfg);dt=2e-14;new,r=advance(cfg,old,dt,impulses_J=impulses)
    C=1.5*1.380649e-23*1e25;V=1e-20;qn=dt/(3e-13);qp=dt/(2e-13)
    matrix=np.array([[1+qn,0.,-qn],[0.,1+qp,-qp],[-qn*C,-qp*C,1000+(qn+qp)*C]])
    expected=np.linalg.solve(matrix,[400+impulses[0]/V/C,250+impulses[1]/V/C,300000+impulses[2]/V])
    assert np.array(list(map(float,r['temperatures_K'])))==pytest.approx(expected[[2,0,1]],rel=2e-14)
    assert r['independent_audit']['valid'] and not r['complete_device_energy']
    assert audit(cfg,old,new,r,energy_atol_J=1e-27,impulses_J=impulses)['valid']


@pytest.mark.parametrize('a,c',[(.6,-.2),(-.4,.3),(-20000.,20000.),(20000.,-20000.),(-2000.,0.)])
def test_nonlinear_log_laws_match_independent_scalar_root_and_saved_audit(a,c):
    cfg=config(a,c);old=initial(cfg);dt=2e-14;new,r=advance(cfg,old,dt)
    C=1.5*1.380649e-23*1e25
    def residual(T):
        logtau=np.log([3e-13,2e-13])+a*np.log(T/150)+c*np.log(2.)
        lost=np.exp(-np.logaddexp(0.,logtau-np.log(dt)))
        return 1000*(T-300)-np.dot(lost,C*(np.array([400.,250.])-T))
    expected=brentq(residual,250.,450.,xtol=1e-11)
    assert float(r['temperatures_K'][0])==pytest.approx(expected,abs=1e-9)
    assert r['independent_audit']['valid']
    if a==-2000.:
        assert min(map(Decimal,r['log_relaxation_times_s']))<Decimal('-1000')
        assert Decimal(new.raw_state[4])>0>Decimal(new.raw_state[5])
        assert abs(Decimal(new.raw_state[4]))<Decimal('1e-500')
    for dt2 in (5e-14,9e-14):
        previous=new;new,r=advance(cfg,new,dt2)
        assert new.raw_state[6:-1]==previous.raw_state[6:]
        if a in (-20000.,-2000.):assert Decimal(new.raw_state[-1])!=0
        assert audit(cfg,previous,new,r,energy_atol_J=1e-27)['valid']


@pytest.mark.parametrize('tail',['1e-300','-1e-300'])
def test_three_micro_steps_retain_signed_lattice_expansion(tail):
    cfg=config();state=initialize(cfg,[1e25,1e25],300.,[300.,300.,300.])
    state=replace(state,raw_state=(*state.raw_state[:4],tail,'0'))
    for dt in (2e-14,5e-14,9e-14):
        old=state;state,r=advance(cfg,state,dt)
        assert state.raw_state[6:-1]==old.raw_state[6:]
        assert Decimal(state.raw_state[-1])!=0
        assert audit(cfg,old,state,r,energy_atol_J=1e-27)['valid']


def test_saved_lattice_history_cannot_be_rewritten(stiff_saved):
    cfg,old,new,r=stiff_saved
    second,r2=advance(cfg,new,5e-14)
    forged=replace(second,raw_state=(*second.raw_state[:6],'0',*second.raw_state[7:]))
    with pytest.raises(ValueError,match='history'):audit(cfg,new,forged,r2,energy_atol_J=1e-27)


def test_domain_envelope_rejects_a_resolved_boundary_violation():
    cfg=config();old=initial(cfg);new,r=advance(cfg,old,2e-14)
    with localcontext() as ctx:
        ctx.prec=100
        C=Decimal('1.5')*Decimal('1.380649e-23')*Decimal(old.raw_state[1])
        tail=str(Decimal(old.raw_state[5])-C*Decimal('1e-20'))
    forged=replace(old,raw_state=(*old.raw_state[:5],tail))
    with pytest.raises(ValueError,match='domain'):audit(cfg,forged,new,r,energy_atol_J=1e-27)


@pytest.mark.parametrize('energy',['1e-80','-1e-80','1e-300','-1e-300'])
def test_tiny_carrier_transfer_preserves_nonzero_lattice_primary_energy(energy):
    cfg=config();old=initialize(cfg,[1e25,1e25],300.,[300.,300.,300.])
    old=replace(old,raw_state=(*old.raw_state[:4],energy,'0'))
    new,r=advance(cfg,old,2e-14)
    assert Decimal(new.raw_state[-1])!=0 and float(r['temperatures_K'][0])==300.
    assert Decimal(new.raw_state[-1]).is_signed()==Decimal(energy).is_signed()
    with localcontext() as ctx:
        ctx.prec=100
        C=Decimal('1.5')*Decimal('1.380649e-23')*Decimal(old.raw_state[0]);L=Decimal(new.raw_state[-1])
        delta_energy=(1+2*C/1000)*L+Decimal(new.raw_state[4])+Decimal(new.raw_state[5])-Decimal(energy)
        assert abs(delta_energy/Decimal(energy))<Decimal('1e-28')
    assert r['independent_audit']['valid']


@pytest.fixture(scope='module')
def stiff_saved():
    cfg=config(-2000.,0.);old=initial(cfg);new,r=advance(cfg,old,2e-14)
    return cfg,old,new,r


@pytest.mark.parametrize('damage',['drop_tail','double_tail','lattice','exchange','storage','residual','logtau','temperature','source',
                                    'density','clock','fingerprint','scope','complete','validated','coverage','nan','evaluations'])
def test_independent_audit_rejects_damaged_saved_records(stiff_saved,damage):
    cfg,old,new,source=stiff_saved;r=deepcopy(source)
    if damage in ('drop_tail','double_tail'):
        tail='0' if damage=='drop_tail' else str(Decimal(new.raw_state[4])*2)
        new=replace(new,raw_state=(*new.raw_state[:4],tail,*new.raw_state[5:]));r['independent_audit']={'valid':True}
    elif damage=='lattice':new=replace(new,raw_state=(*new.raw_state[:3],'1',*new.raw_state[4:]))
    elif damage=='exchange':r['exchange_J'][0]='1e-10'
    elif damage=='storage':r['energy_increments_J'][0]='1e-10'
    elif damage=='residual':r['residuals_J'][0]='1e-10'
    elif damage=='logtau':r['log_relaxation_times_s'][0]='0'
    elif damage=='temperature':r['temperatures_K'][0]='350'
    elif damage=='source':r['impulses_J'][0]='1e-10'
    elif damage=='density':new=replace(new,raw_state=('2e25',*new.raw_state[1:]))
    elif damage=='clock':new=replace(new,time_s=new.time_s*2)
    elif damage=='fingerprint':r['configuration_sha256']='bad'
    elif damage=='scope':r['scope']='complete_device'
    elif damage=='complete':r['complete_device_energy']=True
    elif damage=='validated':r['physical_validated']=True
    elif damage=='coverage':r['exchange_J']=[]
    elif damage=='nan':r['exchange_J'][0]='NaN'
    elif damage=='evaluations':r['residual_evaluations']=True
    try:valid=audit(cfg,old,new,r,energy_atol_J=1e-27)['valid']
    except ValueError:valid=False
    assert not valid


def test_offline_audit_uses_no_native_or_production_law(stiff_saved,monkeypatch):
    cfg,old,new,r=stiff_saved
    import tcad.core._bindings as native
    def deny(*a,**kw):raise AssertionError('native/production physics in independent audit')
    for name in dir(native):
        if (name.startswith('native_') or name.startswith('three_temperature_')) and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    monkeypatch.setattr(Law,'evaluate',deny)
    assert audit(cfg,old,new,r,energy_atol_J=1e-27)['valid']


def test_zero_equilibrium_cannot_gain_an_arbitrarily_small_forged_tail():
    cfg=config();old=initialize(cfg,[1e25,1e25],300.,[300.,300.,300.]);new,r=advance(cfg,old,2e-14)
    forged=replace(new,raw_state=(*new.raw_state[:4],'1e-100',*new.raw_state[5:]))
    assert not audit(cfg,old,forged,r,energy_atol_J=1e-27)['valid']


def test_failed_step_or_failed_audit_never_changes_immutable_input(monkeypatch):
    cfg=config(-20000.,20000.);old=initial(cfg);saved=old.raw_state
    with pytest.raises(RuntimeError,match='budget exhausted'):advance(cfg,old,2e-14,max_nfev=1)
    assert old.raw_state==saved
    with monkeypatch.context() as p:
        p.setattr('tcad.postprocess.boltzmann_relaxation.audit_mb_relaxation_step',lambda *a,**k:dict(valid=False))
        with pytest.raises(ValueError,match='independent MB'):advance(cfg,old,2e-14)
    assert old.raw_state==saved
    a,ra=advance(cfg,old,2e-14);b,rb=advance(cfg,old,2e-14)
    assert a==b and ra==rb
    with pytest.raises(FrozenInstanceError):old.time_s=1.
    with pytest.raises(FrozenInstanceError):cfg.parameters=()


def test_unsupported_b_and_split_valleys_are_explicitly_rejected():
    with pytest.raises(ValueError):Config.create(1000.,1e-20,3e-13,2e-13,ONE,ONE,laws=(Law(300,1e25,0,1,0),Law()))
    split=(*ONE,ThermionicValley('split',1,.3,.3,.3,1e-21,1e-21))
    with pytest.raises(ValueError):Config.create(1000.,1e-20,3e-13,2e-13,split,ONE)
    cfg=config();old=initial(cfg)
    with pytest.raises(ValueError):raw(old.raw_state,[*cfg.parameters,'2e-14','1e-27','0','0','0'],['.3','.3','1','0','.3','.3','1','1e-21'],cfg.valleys_p)


@pytest.mark.parametrize('budget',[True,0,-1,4097,1.5])
def test_invalid_evaluation_budgets_rejected(budget):
    cfg=config();old=initial(cfg)
    with pytest.raises(ValueError):advance(cfg,old,2e-14,max_nfev=budget)


@pytest.mark.parametrize('damage',['negative_density','invalid_state','unbracketed_source','unrepresentable_tail'])
def test_invalid_or_unrepresentable_states_fail_without_clipping(damage):
    cfg=config();old=initial(cfg)
    if damage=='negative_density':
        with pytest.raises(ValueError):initialize(cfg,[-1,1e25],300.,[300.,400.,250.])
    elif damage=='invalid_state':
        bad=replace(old,raw_state=(*old.raw_state[:4],'1e30',old.raw_state[5]))
        with pytest.raises(ValueError):advance(cfg,bad,2e-14)
    elif damage=='unbracketed_source':
        with pytest.raises((ValueError,RuntimeError)):advance(cfg,old,2e-14,impulses_J=(1.,0.,0.))
    else:
        cfg=config(-200000.,0.);old=initial(cfg)
        with pytest.raises((ValueError,RuntimeError)):advance(cfg,old,2e-14)
