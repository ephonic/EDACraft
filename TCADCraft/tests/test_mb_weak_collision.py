from copy import deepcopy
from dataclasses import asdict,replace
from fractions import Fraction
import pytest
from tcad.core import _weak_collision_mb as native,_recomputed_mb as legacy
from tcad.physics.native_fermi_local import _decimal
from tcad.solver.boltzmann_weak_endpoint_collision import advance_mb_weak_endpoint_collision as advance
from tcad.postprocess.boltzmann_weak_endpoint_collision import audit_mb_weak_endpoint_collision as audit
from tcad.postprocess.boltzmann_weak_endpoint_powerlaw import audit_mb_weak_endpoint_powerlaw as root_audit,split_mb_weak_endpoint_powerlaw as split
from tcad.postprocess.boltzmann_recomputed_endpoint_powerlaw import audit_mb_recomputed_endpoint_powerlaw as old_audit
from tcad.postprocess.boltzmann_scaled_split import _saved_fingerprint
from tcad.postprocess.boltzmann_recomputed_transport import _wire
from docs.validation.mb_weak_collision_20261024.cases import control

@pytest.fixture(scope='module')
def actual():
    c,states,q=control();new,r=advance(c['configurations'][0],states[0],2.**-52,impulses_J=q[0])
    return c,states[0],q[0],new,r

def constant(ratio):
    c,states,q=control(dt=2.**-50);cfg=deepcopy(c['configurations'][0]);p=cfg['parameters']
    p[2]=p[3]=_decimal(ratio*2.**-50)
    for j in (6,7,10,11):p[j]='0'
    return cfg,states[0],q[0]

@pytest.mark.parametrize('ratio',[1/256,1,1000,1001,2048,4096])
def test_finite_weak_domain_preserves_actual_energy_and_exact_coefficient(ratio):
    cfg,old,q=constant(ratio);before=asdict(old);new,r=advance(cfg,old,2.**-50,impulses_J=q)
    check=audit(cfg,old,new,r,dt_s=2.**-50,impulses_J=q)
    assert check['valid'] and check['actual_endpoint_graph_checked'] and len(check['residuals'])==6
    assert check['root']['weak_collision_coefficient_gate_passed']
    assert all(Fraction(x)<=4*Fraction(1,2**112) for x in check['root']['coefficient_relative_errors'])
    assert asdict(old)==before and not r['physical_validated'] and not r['complete_device_energy']
    assert native.precision_bits==113

@pytest.mark.parametrize('ratio',[1/2048,4097])
def test_both_native_domain_edges_still_reject(ratio):
    cfg,old,q=constant(ratio);before=asdict(old)
    with pytest.raises(ValueError,match='outside tested range'):advance(cfg,old,2.**-50,impulses_J=q)
    assert asdict(old)==before

@pytest.mark.parametrize('multiplier',[1,2,4])
def test_overlap_packet_is_identical_except_version(multiplier):
    dt=2.**-50*multiplier;c,states,imp=control(dt=dt);cfg=c['configurations'][0];old=states[0];q=imp[0];command=[*cfg['parameters'],_decimal(dt),*map(_decimal,q)]
    a=legacy.native_mb_recomputed_endpoint_powerlaw_raw(old.endpoint,command,old.physical_clock)
    b=native.native_mb_weak_endpoint_powerlaw_raw(old.endpoint,command,old.physical_clock)
    assert a[1:]==b[1:] and a[0]!=b[0]
    assert old_audit(old.endpoint,command,old.physical_clock,a)['valid']

@pytest.mark.parametrize('ratio',[1001,2048,4096])
def test_legacy_guard_remains_unchanged(ratio):
    cfg,old,q=constant(ratio);command=[*cfg['parameters'],_decimal(2.**-50),*map(_decimal,q)]
    with pytest.raises(ValueError,match='1e-3<=tau/dt<=1e3'):legacy.native_mb_recomputed_endpoint_powerlaw_raw(old.endpoint,command,old.physical_clock)

@pytest.mark.parametrize('damage',['source','dt','config','clock','endpoint','metadata','packet','version','precision','history'])
def test_rehashed_actual_endpoint_and_root_forgeries_are_rejected(actual,damage):
    c,old,q,new,r=actual;cfg=deepcopy(c['configurations'][0]);r=deepcopy(r);q=list(q);dt=2.**-52
    if damage=='source':q[0]*=2
    elif damage=='dt':dt*=2
    elif damage=='config':cfg['parameters'][6]='0.7'
    elif damage=='clock':new=replace(new,time_s=new.time_s*2,physical_clock=tuple(_wire(Fraction(new.time_s)*2)))
    elif damage=='endpoint':new=replace(new,endpoint=old.endpoint)
    elif damage=='metadata':r['complete_device_energy']=True
    elif damage=='packet':r['root_packet'][-1]='bad'
    elif damage=='version':r['root_packet'][0]='mb_recomputed_endpoint_powerlaw_v1'
    elif damage=='precision':r['root_packet'][1]='64'
    else:r['root_packet'][8]=_decimal(1e-10)
    r['new_sha256']=_saved_fingerprint(new)
    with pytest.raises((ValueError,ArithmeticError)):audit(cfg,old,new,r,dt_s=dt,impulses_J=q)

def test_native_extreme_a_still_rejected_before_materialization(actual):
    c,old,q,new,r=actual;cfg=deepcopy(c['configurations'][0]);cfg['parameters'][6]='-20000'
    with pytest.raises(ValueError,match=r'abs\(a,c\)<=8'):advance(cfg,old,2.**-52,impulses_J=q)

def test_forged_root_is_rejected_before_materializer(actual,monkeypatch):
    c,old,q,new,r=actual;raw=deepcopy(r['root_packet']);raw[0]='forged';calls=[]
    monkeypatch.setattr(native,'native_mb_weak_endpoint_powerlaw_raw',lambda *args:raw)
    monkeypatch.setattr(native,'native_mb_recomputed_endpoint_apply_raw',lambda *args:calls.append(args))
    with pytest.raises(ValueError):advance(c['configurations'][0],old,2.**-52,impulses_J=q)
    assert not calls

def test_independent_auditor_uses_no_native_function(actual,monkeypatch):
    c,old,q,new,r=actual
    def deny(*a,**kw):raise AssertionError('native forbidden')
    for module in (native,legacy):
        for name in vars(module):
            if name.startswith('native_'):monkeypatch.setattr(module,name,deny)
    assert audit(c['configurations'][0],old,new,r,dt_s=2.**-52,impulses_J=q)['valid']

def test_old_auditor_rejects_new_protocol(actual):
    c,old,q,new,r=actual
    with pytest.raises(ValueError,match='version/precision'):old_audit(old.endpoint,r['command'],old.physical_clock,r['root_packet'])

def test_constant_tau_preserves_exact_reference_at_upper_boundary():
    cfg,old,q=constant(4096);new,r=advance(cfg,old,2.**-50,impulses_J=q)
    assert list(map(Fraction,split(r['root_packet'])['chosen'][1:]))==list(map(Fraction,cfg['parameters'][2:4]))
