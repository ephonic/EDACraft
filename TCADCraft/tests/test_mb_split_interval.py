from copy import deepcopy
from dataclasses import asdict,replace
from decimal import Decimal,localcontext
import pytest
from tests.test_mb_particle_energy import make,expand
from tests.test_mb_affine_temperature_domain import hot,coordinate_case
from tcad.solver.boltzmann_split_interval import advance_mb_split_interval as advance
from tcad.solver.boltzmann_affine_powerlaw import advance_mb_affine_powerlaw
from tcad.postprocess.boltzmann_split_interval import audit_mb_split_interval as audit
from tcad.postprocess.boltzmann_affine_transport import _fingerprint,_point,_Arithmetic

DT=2e-14;EDGE=dict(owner=0,neighbor=1,geometry=(1e-18,1e-8,2e-8,.1,.2))

def problem(mode='closed'):
    cfg,s=make(.6,-.2);a=expand(cfg,s);b=replace(a,electron_excess=(*a.electron_excess,'1000'))
    faces=[] if mode=='isolated' else [EDGE]
    if mode in ('contact','mixed'):
        contact=dict(owner=0,reservoir=b,geometry=(1e-18,1e-8,0.,.1,.2))
        faces=[contact] if mode=='contact' else [EDGE,contact]
    return (cfg,cfg),(a,b),faces

@pytest.mark.parametrize('mode',['isolated','closed','contact','mixed'])
def test_admitted_split_steps_with_sources_and_contacts(mode):
    cfg,states,faces=problem(mode);q=((2e-19,-1e-19,3e-19),(0.,0.,0.))
    start=states[0].time_s
    for _ in range(2 if mode=='isolated' else 1):
        faces=[{**f,'reservoir':replace(f['reservoir'],time_s=states[0].time_s)} if 'reservoir' in f else f for f in faces]
        old=states;states,r=advance(cfg,states,faces,DT,impulses_J=q)
        assert states[0].time_s==old[0].time_s+DT
        assert r['independent_audit']['whole_interval_particle_energy_closed']
        assert audit(cfg,old,states,r,faces=faces,dt_s=DT,impulses_J=q)['valid']
    assert states[0].time_s==start+(2 if mode=='isolated' else 1)*DT

def test_isolated_split_exactly_matches_single_collision_physical_state():
    cfg,s=make(.6,-.2);old=expand(cfg,s)
    (new,),r=advance((cfg,),(old,),[],DT)
    direct,_=advance_mb_affine_powerlaw(cfg,old,DT)
    assert asdict(new)==asdict(direct) and r['auxiliary_collision_end_s']==2*DT

@pytest.mark.parametrize('mode',['hot','coordinate_hot','coordinate_cold'])
def test_compensated_and_original_hot_inputs(mode):
    cfg,state=hot() if mode=='hot' else coordinate_case(310000 if mode=='coordinate_hot' else -150000)
    (new,),r=advance((cfg,),(state,),[],DT)
    assert r['independent_audit']['valid'] and new.time_s==state.time_s+DT

@pytest.mark.parametrize('tail',['1e-300','-1e-300'])
def test_density_microtails_preserved_across_split(tail):
    from tcad.solver.boltzmann_frozen_finite_volume import MBFiniteVolumeState
    cfg,s=make(.6,-.2);a=expand(cfg,s);a=MBFiniteVolumeState(a,(tail,),(),(),(),1e-18)
    (new,),r=advance((cfg,),(a,),[],DT)
    assert new.electron_density_change==a.electron_density_change and r['independent_audit']['valid']

@pytest.mark.parametrize('damage',['clock_twice','aux_clock','interval','stage','child_dt','metadata','source','compensation'])
def test_rehashed_whole_interval_forgeries_rejected(damage):
    cfg,old,faces=problem();new,r=advance(cfg,old,faces,DT);r=deepcopy(r)
    if damage=='clock_twice':new=(replace(new[0],time_s=2*DT),new[1]);r['new_sha256']=list(map(_fingerprint,new))
    if damage=='aux_clock':r['auxiliary_collision_end_s']=DT
    if damage=='interval':r['physical_interval_s'][1]=2*DT
    if damage=='stage':r['transported_states'][0]['electron_density_change'].append('1e-300') if isinstance(r['transported_states'][0]['electron_density_change'],list) else r['transported_states'][0].update(electron_density_change=(*r['transported_states'][0]['electron_density_change'],'1e-300'))
    if damage=='child_dt':r['collisions'][0]['dt_s']='1e-14'
    if damage=='metadata':r['monolithic_coupled_BE']=True
    if damage=='source':r['collisions'][0]['collision']['impulses_J'][0]='1e-30'
    if damage=='compensation':new=(replace(new[0],electron_energy_density_change=()),new[1]);r['new_sha256']=list(map(_fingerprint,new))
    try:check=audit(cfg,old,new,r,faces=faces,dt_s=DT)
    except (ValueError,ArithmeticError):return
    assert not check['valid']

@pytest.mark.parametrize('damage',['configuration_count','source_count','unsynchronized','negative_dt','bad_face'])
def test_bad_request_is_atomic(damage):
    cfg,old,faces=problem();before=deepcopy(asdict(old[0]));q=None;dt=DT
    if damage=='configuration_count':cfg=cfg[:1]
    if damage=='source_count':q=((0.,0.,0.),)
    if damage=='unsynchronized':old=(old[0],replace(old[1],time_s=1e-18))
    if damage=='negative_dt':dt=-DT
    if damage=='bad_face':faces=[{**EDGE,'neighbor':0}]
    with pytest.raises(ValueError):advance(cfg,old,faces,dt,impulses_J=q)
    assert asdict(old[0])==before

def test_independent_saved_replay_without_native_or_production(monkeypatch):
    cfg,old,faces=problem();new,r=advance(cfg,old,faces,DT);r.pop('independent_audit')
    import tcad.core._bindings as native
    import tcad.solver.boltzmann_split_interval as split
    import tcad.solver.boltzmann_affine_powerlaw as collision
    import tcad.solver.boltzmann_nonisothermal_transport as transport
    from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw
    def deny(*a,**kw):raise AssertionError('production call during independent split replay')
    for k in dir(native):
        if k.startswith(('native_','three_temperature_')) and callable(getattr(native,k)):monkeypatch.setattr(native,k,deny)
    for module,name in ((split,'advance_mb_split_interval'),(collision,'advance_mb_affine_powerlaw'),(transport,'advance_mb_nonisothermal_transport')):monkeypatch.setattr(module,name,deny)
    monkeypatch.setattr(EnergyRelaxationPowerLaw,'evaluate',deny)
    assert audit(cfg,old,new,r,faces=faces,dt_s=DT)['valid']

def constant_problem():
    cfg,states,faces=problem('isolated');configurations=[]
    for c in cfg:
        p=list(c.parameters)
        for j in (6,7,10,11):p[j]='0'
        configurations.append(replace(c,parameters=tuple(p)))
    return tuple(configurations),states,faces


def exact_isolated_temperatures(config,state,duration):
    # Independent analytic 2x2 carrier-minus-lattice system, constant n/Cv/tau.
    with localcontext() as ctx:
        ctx.prec=180;p=_point(state,_Arithmetic());f=p['frame'];alpha=Decimal('1.5')*Decimal('1.380649e-23')
        cn,cp=[alpha*x for x in p['n']];cv=f[3];tn,tp=map(Decimal,config.parameters[2:4]);t=Decimal.from_float(duration)
        a=-(1+cn/cv)/tn;b=-cp/(cv*tp);c=-cn/(cv*tn);d=-(1+cp/cv)/tp
        h=(a+d)/2;v=(((a-d)/2)**2+b*c).sqrt();ep=(v*t).exp();em=(-v*t).exp()
        ch=(ep+em)/2;sh=(ep-em)/(2*v);factor=(h*t).exp();tl,x,y=p['temperatures'];x-=tl;y-=tl
        xx=factor*((ch+sh*(a-h))*x+sh*b*y);yy=factor*(sh*c*x+(ch+sh*(d-h))*y)
        energy=cv*tl+cn*(tl+x)+cp*(tl+y);lattice=(energy-cn*xx-cp*yy)/(cv+cn+cp)
        return [lattice,lattice+xx,lattice+yy]


def test_constant_tau_isolated_time_refinement_against_exact_solution():
    cfg,initial,faces=constant_problem();values=[]
    exact=[x for c,s in zip(cfg,initial) for x in exact_isolated_temperatures(c,s,DT)]
    for count in (1,2,4):
        states=initial
        for _ in range(count):states,_=advance(cfg,states,faces,DT/count)
        with localcontext() as ctx:
            ctx.prec=10000;values.append([x for s in states for x in _point(s,_Arithmetic())['temperatures']])
    with localcontext() as ctx:
        ctx.prec=10000;errors=[sum(abs(a-b) for a,b in zip(v,exact)) for v in values]
        assert errors[0]>errors[1]>errors[2]>0


@pytest.mark.parametrize('mode',['closed','contact','mixed'])
def test_second_spatial_split_rejects_range_exhaustion_atomically(mode):
    cfg,old,faces=problem(mode);q=((2e-19,-1e-19,3e-19),(0.,0.,0.))
    states,_=advance(cfg,old,faces,DT,impulses_J=q);before=[asdict(s) for s in states]
    faces=[{**f,'reservoir':replace(f['reservoir'],time_s=states[0].time_s)} if 'reservoir' in f else f for f in faces]
    with pytest.raises(ValueError,match='MB expansion arithmetic normal range exceeded'):
        advance(cfg,states,faces,DT,impulses_J=q)
    assert [asdict(s) for s in states]==before
