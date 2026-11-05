from dataclasses import replace
from copy import deepcopy
from decimal import Decimal,localcontext
import numpy as np
import pytest
from tcad.solver.boltzmann_relaxation import MBRelaxationConfiguration as Config,initialize_mb_relaxation as initialize,advance_mb_relaxation as advance
from tcad.solver.boltzmann_particle_energy import expand_mb_relaxation_state as expand,update_mb_particle_energy as update,MBParticleEnergyState
from tcad.postprocess.boltzmann_particle_energy import audit_mb_particle_energy as audit
from tcad.physics.multivalley_thermionic import ThermionicValley
from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw as Law
from tcad.core._bindings import native_boltzmann_particle_energy_raw as raw

ONE=(ThermionicValley('one',1,.3,.3,.3),)
def make(a=0,c=0):
    law=Law(150.,5e24,a,0,c)
    cfg=Config.create(1000.,1e-20,3e-13,2e-13,ONE,ONE,laws=(law,law),temperature_bounds=(150.,700.))
    return cfg,initialize(cfg,[1e25,1e25],300.,[310.,400.,250.])


@pytest.mark.parametrize('densities,bands,q',[
    ([1.1e25,.9e25],[0.,0.],[0.,0.]),
    ([1e25,1e25],[1e-21,-1e-21],[0.,0.]),
    ([.8e25,1.2e25],[-1e-21,1e-21],[2e-19,-1e-19]),
    ([1e25,1e25],[0.,0.],[1e-300,-1e-300]),
    ([1e25,1e25],[0.,0.],[0.,0.]),
])
def test_independent_MB_total_energy_and_temperature(densities,bands,q):
    cfg,s=make();old=expand(cfg,s);new,r=update(old,densities,bands,energy_impulses_J=q)
    with localcontext() as ctx:
        ctx.prec=500
        alpha=Decimal('1.5')*Decimal('1.380649e-23');f=list(map(Decimal,old.frame));g=list(map(Decimal,new.frame))
        Tl=f[2]+sum(f[9:])/f[3]
        for k,field in enumerate(('electron_excess','hole_excess')):
            U=f[k]*(f[5+k]+alpha*Tl)+sum(map(Decimal,getattr(old,field)))
            expected=((U+Decimal.from_float(q[k])/f[4])/g[k]-g[5+k])/alpha
            assert float(r['temperatures_K'][k+1])==pytest.approx(float(expected),rel=1e-14)
    assert r['independent_audit']['valid'] and new.time_s==old.time_s


@pytest.mark.parametrize('tail',['1e-300','-1e-300','1e-1863','-1e-1863'])
def test_finite_background_and_roundtrip_keep_tiny_authoritative_tail(tail):
    cfg,s=make();old=expand(cfg,s)
    old=replace(old,electron_excess=(tail,),hole_excess=(tail,))
    new,r=update(old,[1.1e25,.9e25],[1e-21,-1e-21])
    back,rr=update(new,[float(old.frame[0]),float(old.frame[1])],[0.,0.])
    assert new.electron_excess[0]==back.electron_excess[0]==tail
    assert new.hole_excess[0]==back.hole_excess[0]==tail
    with localcontext() as ctx:
        ctx.prec=3000
        for field in ('electron_excess','hole_excess'):
            total=sum(map(Decimal,getattr(back,field)))
            # Decimal export has finite rounding; its finite-background error
            # must obey the audit budget. Component provenance preserves the tail.
            assert abs(total-Decimal(tail))<Decimal('1e-27')
    assert r['independent_audit']['valid'] and rr['independent_audit']['valid']


@pytest.mark.parametrize('a,c',[(-20000.,20000.),(-2000.,0.),(.6,-.2)])
def test_real_stiff_collision_saved_tail_is_preserved_through_density_band_update(a,c):
    cfg,s=make(a,c)
    for dt in (2e-14,5e-14,9e-14):s,r=advance(cfg,s,dt)
    old=expand(cfg,s);new,r=update(old,[1.01e25,.99e25],[1e-22,-1e-22])
    assert new.electron_excess[0]==s.raw_state[4] and new.hole_excess[0]==s.raw_state[5]
    assert new.frame[9:]==old.frame[9:]
    assert Decimal(new.electron_excess[0])!=0 and r['independent_audit']['valid']


def test_saved_audit_uses_no_native_physics(monkeypatch):
    cfg,s=make();old=expand(cfg,s);new,r=update(old,[1.1e25,.9e25],[0.,0.])
    import tcad.core._bindings as native
    def deny(*a,**kw):raise AssertionError('native physics used')
    for name in dir(native):
        if name.startswith('native_') and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    assert audit(old,new,r,densities=[1.1e25,.9e25],bands_J=[0.,0.],energy_impulses_J=[0.,0.],energy_atol_J=1e-27)['valid']


@pytest.mark.parametrize('forgery',['tail','append','density','band','clock','lattice','source','metadata','view'])
def test_forged_saved_transaction_rejected(forgery):
    cfg,s=make();old=expand(cfg,s);new,r=update(old,[1.1e25,.9e25],[0.,0.]);r=deepcopy(r)
    if forgery=='tail':new=replace(new,electron_excess=('0',*new.electron_excess[1:]))
    if forgery=='append':new=replace(new,electron_excess=(*new.electron_excess,'1'))
    if forgery=='density':new=replace(new,frame=('1e25',*new.frame[1:]))
    if forgery=='band':new=replace(new,frame=(*new.frame[:5],'1e-20',*new.frame[6:]))
    if forgery=='clock':new=replace(new,time_s=1.)
    if forgery=='lattice':new=replace(new,frame=(*new.frame[:9],'0',*new.frame[10:]))
    if forgery=='source':r['energy_impulses_J'][0]='1e-20'
    if forgery=='metadata':r['complete_device_energy']=True
    if forgery=='view':r['temperatures_K'][1]='300'
    try:result=audit(old,new,r,densities=[1.1e25,.9e25],bands_J=[0.,0.],energy_impulses_J=[0.,0.],energy_atol_J=1e-27)
    except ValueError:return
    assert not result['valid']


@pytest.mark.parametrize('n,e,q',[
    ([0.,1e25],[0.,0.],[0.,0.]),([-1.,1e25],[0.,0.],[0.,0.]),
    ([1e25,1e25],[float('nan'),0.],[0.,0.]),
    ([1e25,1e25],[0.,0.],[1.,0.]),
    ([1e50,1e25],[0.,0.],[0.,0.]),
])
def test_bad_commands_fail_without_mutation(n,e,q):
    cfg,s=make();old=expand(cfg,s);before=deepcopy(old)
    with pytest.raises((ValueError,RuntimeError)):update(old,n,e,energy_impulses_J=q)
    assert old==before


def test_component_limit_and_unrepresentable_product_reject():
    cfg,s=make();old=expand(cfg,s)
    crowded=replace(old,electron_excess=('0',)*4096)
    with pytest.raises(ValueError):update(crowded,[1.1e25,.9e25],[0.,0.])
    f=list(old.frame);f[9]='1e-3990';f[0]='1e-1000';f[1]='1e-1000'
    with pytest.raises(ValueError):raw(f,['0'],['0'],['2e-1000','1e-1000','0','0','0','0'])


def test_raw_precision_and_compensation_without_float_bridge():
    cfg,s=make();old=expand(cfg,s)
    r=raw(old.frame,old.electron_excess,old.hole_excess,['1.00000000000000000000000000000001e25',old.frame[1],'0','0','0','0'])
    assert Decimal(r[0])!=Decimal(old.frame[0]) and float(r[0])==float(old.frame[0])


def test_zero_command_cannot_hide_microscopic_new_energy_under_absolute_gate():
    cfg,s=make();old=expand(cfg,s);new,r=update(old,[float(old.frame[0]),float(old.frame[1])],[0.,0.])
    new=replace(new,electron_excess=(*new.electron_excess,'1e-300'))
    assert not audit(old,new,r,densities=[float(old.frame[0]),float(old.frame[1])],bands_J=[0.,0.],energy_impulses_J=[0.,0.],energy_atol_J=1e-27)['valid']
