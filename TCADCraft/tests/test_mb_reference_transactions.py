from dataclasses import replace
from copy import deepcopy
from decimal import Decimal,localcontext
import numpy as np
import pytest
from tcad.solver.boltzmann_relaxation import MBRelaxationConfiguration as Config,initialize_mb_relaxation as initialize,advance_mb_relaxation as advance
from tcad.solver.boltzmann_rebase import rebase_mb_reference as rebase
from tcad.postprocess.boltzmann_rebase import audit_mb_reference_rebase as audit_rebase
from tcad.postprocess.boltzmann_relaxation import audit_mb_relaxation_step as audit_step
from tcad.physics.multivalley_thermionic import ThermionicValley
from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw as Law
from tcad.core._bindings import native_boltzmann_reference_rebase_raw as raw

ONE=(ThermionicValley('one',1,.3,.3,.3),)
def config(a=0,c=0,Cv=1000.):
    law=Law(150.,5e24,a,0,c)
    return Config.create(Cv,1e-20,3e-13,2e-13,ONE,ONE,laws=(law,law),temperature_bounds=(200.,500.))
def initial(cfg):return initialize(cfg,[1e25,1e25],300.,[300.,400.,250.])


@pytest.mark.parametrize('reference',[300.,350.125,1.001,99998.,123.456789,np.longdouble('312.123456789123456789')])
def test_reference_rebase_and_back_preserve_tails_history_clock_and_temperatures(reference):
    cfg=config(Cv=np.longdouble('1234.567890123456789'));old=initial(cfg)
    old,r0=advance(cfg,old,2e-14);new,r=rebase(cfg,old,reference)
    assert new.time_s==old.time_s and new.raw_state[:2]==old.raw_state[:2]
    assert new.raw_state[3:6]==old.raw_state[3:6] and new.raw_state[6:-4]==old.raw_state[6:]
    assert r['independent_audit']['valid']
    assert list(map(float,r['temperatures_K']))==pytest.approx(list(map(float,r['old_temperatures_K'])),abs=1e-10)
    back,rb=rebase(cfg,new,300.)
    with localcontext() as ctx:
        ctx.prec=800
        assert sum(map(Decimal,back.raw_state[-8:]))==0
    assert back.raw_state[4:6]==old.raw_state[4:6]
    expected,er=advance(cfg,old,5e-14);actual,ar=advance(cfg,back,5e-14)
    assert list(map(float,ar['temperatures_K']))==pytest.approx(list(map(float,er['temperatures_K'])),rel=1e-14)
    assert audit_step(cfg,back,actual,ar,energy_atol_J=1e-27)['valid']


@pytest.mark.parametrize('a,c',[(-20000.,20000.),(-2000.,0.),(.6,-.2)])
def test_stiff_collision_rebase_collision_transaction(a,c):
    cfg=config(a,c);state=initial(cfg)
    for dt,reference in zip((2e-14,5e-14,9e-14),(350.125,250.5,300.)):
        state,r=advance(cfg,state,dt);before=state
        state,rr=rebase(cfg,state,reference)
        assert state.raw_state[4:6]==before.raw_state[4:6]
        assert audit_rebase(cfg,before,state,rr,reference_temperature_K=reference,energy_atol_J=1e-27)['valid']
        if a<0:assert Decimal(state.raw_state[4])!=0 and Decimal(state.raw_state[5])!=0


@pytest.mark.parametrize('tail',['1e-300','-1e-300','1e-1863','-1e-1863'])
def test_reference_round_trip_retains_micro_journal_components(tail):
    cfg=config();old=initialize(cfg,[1e25,1e25],300.,[300.,300.,300.])
    old=replace(old,raw_state=(*old.raw_state[:4],tail,'0',tail))
    new,r=rebase(cfg,old,350.125);back,rb=rebase(cfg,new,300.)
    assert back.raw_state[6]==tail and back.raw_state[4]==tail
    with localcontext() as ctx:
        ctx.prec=2000
        assert sum(map(Decimal,back.raw_state[6:]))==Decimal(tail)


def test_raw_native_reference_finer_than_longdouble_uses_compensated_products():
    cfg=config();cfg=replace(cfg,parameters=('1.23456789012345678901234567890123456e3',*cfg.parameters[1:]))
    old=initial(cfg);reference='3.12123456789123456789012345678912345e2'
    result=raw(old.raw_state,cfg.parameters,cfg.valleys_n,cfg.valleys_p,reference)
    assert Decimal(result[2])!=Decimal('312.123456789123456789')
    assert any(Decimal(x)!=0 for x in result[len(old.raw_state)+1:len(old.raw_state)+4:2])
    with localcontext() as ctx:
        ctx.prec=100
        error=sum(map(Decimal,result[len(old.raw_state):len(old.raw_state)+4]))+Decimal(cfg.parameters[0])*(Decimal(result[2])-Decimal(old.raw_state[2]))
        assert abs(error)<Decimal('1e-28')


@pytest.fixture
def saved_rebase():
    cfg=config();old=initial(cfg);new,r=rebase(cfg,old,350.125)
    return cfg,old,new,r


@pytest.mark.parametrize('damage',['density','tail','base','history','clock','reference','terms','scope','source','temperature','cached_audit'])
def test_independent_rebase_audit_rejects_forged_record(saved_rebase,damage):
    cfg,old,new,r=saved_rebase;r=deepcopy(r)
    if damage=='density':new=replace(new,raw_state=('2e25',*new.raw_state[1:]))
    elif damage=='tail':new=replace(new,raw_state=(*new.raw_state[:4],'0',*new.raw_state[5:]))
    elif damage=='base':new=replace(new,raw_state=(*new.raw_state[:3],'1',*new.raw_state[4:]))
    elif damage=='history':new=replace(new,raw_state=(*new.raw_state[:-4],'1',*new.raw_state[-3:]))
    elif damage=='clock':new=replace(new,time_s=1.)
    elif damage=='reference':new=replace(new,raw_state=(*new.raw_state[:2],'350',*new.raw_state[3:]))
    elif damage=='terms':new=replace(new,raw_state=(*new.raw_state[:-1],'1e10'))
    elif damage=='scope':r['complete_device_energy']=True
    elif damage=='source':r['reference_temperature_K']='351'
    elif damage=='temperature':r['temperatures_K'][0]='301'
    elif damage=='cached_audit':
        new=replace(new,raw_state=(*new.raw_state[:-1],'1e10'));r['independent_audit']={'valid':True}
    try:valid=audit_rebase(cfg,old,new,r,reference_temperature_K=350.125,energy_atol_J=1e-27)['valid']
    except ValueError:valid=False
    assert not valid


def test_offline_rebase_audit_calls_no_native_or_production_law(saved_rebase,monkeypatch):
    cfg,old,new,r=saved_rebase
    import tcad.core._bindings as native
    def deny(*a,**kw):raise AssertionError('physical helper used in offline rebase audit')
    for name in dir(native):
        if name.startswith(('native_','three_temperature_')) and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    monkeypatch.setattr(Law,'evaluate',deny)
    assert audit_rebase(cfg,old,new,r,reference_temperature_K=350.125,energy_atol_J=1e-27)['valid']


@pytest.mark.parametrize('reference',[True,0.,1.,1e5,float('nan'),float('inf')])
def test_invalid_reference_does_not_mutate_state(reference):
    cfg=config();old=initial(cfg);saved=old.raw_state
    with pytest.raises(ValueError):rebase(cfg,old,reference)
    assert old.raw_state==saved


def test_unsupported_capacity_and_history_length_are_explicit():
    cfg=config();old=initial(cfg)
    cfg2=replace(cfg,parameters=('1e1001',*cfg.parameters[1:]));old2=replace(old,configuration_sha256=cfg2.sha256)
    with pytest.raises(ValueError):rebase(cfg2,old2,350.)
    long=replace(old,raw_state=(*old.raw_state,*['0']*4087))
    with pytest.raises(ValueError):rebase(cfg,long,350.)


@pytest.mark.parametrize('energy',['1e-80','-1e-80','1e-300','-1e-300'])
@pytest.mark.parametrize('factor',[0,2])
def test_coherent_forgery_below_absolute_J_gate_fails_signal_balance(energy,factor):
    cfg=config();old=initialize(cfg,[1e25,1e25],300.,[300.,300.,300.]);old=replace(old,raw_state=(*old.raw_state[:4],energy,'0'))
    new,r=advance(cfg,old,2e-14)
    with localcontext() as ctx:
        ctx.prec=800
        p=list(map(Decimal,cfg.parameters));s=list(map(Decimal,old.raw_state));dt=Decimal.from_float(r['dt_s']);V=p[1]
        L=Decimal(new.raw_state[-1])*factor;C=[Decimal('1.5')*Decimal('1.380649e-23')*s[k] for k in (0,1)]
        drive=[s[4+k]-C[k]/p[0]*L for k in (0,1)]
        delta=[drive[k]*p[2+k]/(p[2+k]+dt) for k in (0,1)];q=[V*drive[k]*dt/(p[2+k]+dt) for k in (0,1)]
        du=[V*(C[k]/p[0]*L+delta[k]-s[4+k]) for k in (0,1)]+[V*L]
        residual=[du[0]+q[0],du[1]+q[1],du[2]-sum(q),sum(du)]
        forged=replace(new,raw_state=(*old.raw_state[:4],*map(str,delta),*old.raw_state[6:],str(L)))
        r=deepcopy(r);r.update(exchange_J=list(map(str,q)),energy_increments_J=list(map(str,du)),residuals_J=list(map(str,residual)),temperatures_K=['300']*3)
        r['independent_audit']={'valid':True,'signal_energy_valid':True}
    result=audit_step(cfg,old,forged,r,energy_atol_J=1e-27)
    assert all(abs(Decimal(x))<Decimal('1e-27') for x in result['energy_errors_J'])
    assert all(Decimal(x)<Decimal('1e-25') for x in result['constitutive_relative_errors'])
    assert not result['signal_energy_valid'] and not result['valid']
