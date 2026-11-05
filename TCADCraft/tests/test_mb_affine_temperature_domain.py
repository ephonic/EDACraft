from dataclasses import replace,asdict
from decimal import Decimal,localcontext
from copy import deepcopy
import pytest
from tests.test_mb_particle_energy import Config,ONE,Law,expand,initialize,make,update
from tcad.solver.boltzmann_frozen_finite_volume import MBFiniteVolumeState as State
from tcad.solver.boltzmann_affine_powerlaw import advance_mb_affine_powerlaw as nonlinear
from tcad.solver.boltzmann_affine_collision import advance_mb_affine_collision as constant
from tcad.solver.boltzmann_nonisothermal_transport import advance_mb_nonisothermal_transport as transport
from tcad.physics.boltzmann_nonisothermal_face import nonisothermal_mb_flat_face as face
from tcad.postprocess.boltzmann_affine_powerlaw import audit_mb_affine_powerlaw as audit
from tcad.postprocess.boltzmann_affine_transport import _point,_Arithmetic,KB

def hot(a=-6.,c=0.):
    law=Law(150.,5e24,a,0.,c)
    cfg=Config.create(1000.,1e-20,4e-13,4e-13,ONE,ONE,laws=(law,law),temperature_bounds=(150.,700.))
    return cfg,expand(cfg,initialize(cfg,[1e25,1e25],300.,[200.,650.,650.]))

def views(state):
    with localcontext() as ctx:
        ctx.prec=10000;point=_point(state,_Arithmetic());anchor=point['anchor'];f=point['frame']
        fictitious=[point['Tl']+sum(map(Decimal,x))/(Decimal('1.5')*KB*f[k]) for k,x in enumerate((anchor.electron_excess,anchor.hole_excess))]
        return point['temperatures'],fictitious

def coordinate_case(lattice):
    cfg,s=make(.6,-.2);a=expand(cfg,s)
    with localcontext() as ctx:
        ctx.prec=10000;f=list(map(Decimal,a.frame));dT=Decimal(lattice)/f[3]
        stored=[format(-Decimal('1.5')*KB*f[k]*dT,'f') for k in range(2)]
    a=replace(a,frame=(*a.frame,str(lattice)))
    return cfg,State(a,(),(),(stored[0],),(stored[1],),1e-18)

def test_original_650K_rejection_now_commits_and_repeats():
    cfg,old=hot()
    for _ in range(3):
        new,r=nonlinear(cfg,old,2e-14);actual,fake=views(new)
        assert r['independent_audit']['valid'] and max(fake)>700 and min(actual)>150 and max(actual)<700
        assert new.anchor.frame[:len((old.anchor if hasattr(old,'anchor') else old).frame)]==(old.anchor if hasattr(old,'anchor') else old).frame
        old=new

@pytest.mark.parametrize('a,c',[(0.,0.),(.6,-.2),(-2.,.5)])
def test_finite_hot_initial_conditions_across_laws(a,c):
    cfg,old=hot(a,c);new,r=nonlinear(cfg,old,2e-14)
    assert r['independent_audit']['valid'] and max(views(new)[0])<700

@pytest.mark.parametrize('lattice',[310000,-150000])
def test_coordinate_only_outside_view_valid_actual_state(lattice):
    cfg,old=coordinate_case(lattice);actual,fake=views(old)
    assert min(fake)<150 or max(fake)>700
    assert min(actual)>=150 and max(actual)<=700
    new,r=nonlinear(cfg,old,2e-14)
    assert r['independent_audit']['valid'] and new.electron_energy_density_change[:1]==old.electron_energy_density_change

def test_constant_tau_also_uses_actual_full_state():
    cfg,old=hot(0.,0.)
    for _ in range(3):old,r=constant(cfg,old,1e-12)
    assert r['independent_audit']['valid'] and max(views(old)[1])>700

@pytest.mark.parametrize('lattice',[310000,-150000])
def test_face_and_continuous_transport_accept_compensated_coordinates(lattice):
    cfg,a=coordinate_case(lattice);b=replace(a,electron_energy_density_change=(*a.electron_energy_density_change,'1e3'))
    r=face(a,b,(1e-14,1e-8,2e-8,.1,.2));assert r['independent_audit']['valid']
    states,r=transport((a,b),[dict(owner=0,neighbor=1,geometry=(1e-14,1e-8,2e-8,.1,.2))],1e-18)
    assert r['independent_audit']['valid']
    states,r=transport(states,[],1e-18);assert r['independent_audit']['valid']

def test_real_collision_outside_anchor_view_then_transport():
    cfg,a=hot();a,_=nonlinear(cfg,a,2e-14);b=replace(a,electron_energy_density_change=(*a.electron_energy_density_change,'1000'))
    states,r=transport((a,b),[dict(owner=0,neighbor=1,geometry=(1e-14,1e-8,2e-8,.1,.2))],1e-18)
    assert r['independent_audit']['valid'] and all(max(views(s)[1])>700 for s in states)

def test_detached_anchor_is_still_invalid_as_standalone_physical_state():
    cfg,a=hot();a,_=nonlinear(cfg,a,2e-14)
    with pytest.raises(ValueError):update(a.anchor,[1e25,1e25],[0.,0.])
    with pytest.raises(ValueError):nonlinear(cfg,a.anchor,2e-14)
    with localcontext() as ctx:
        ctx.prec=10000
        with pytest.raises(ValueError):_point(a.anchor,_Arithmetic())

@pytest.mark.parametrize('damage',['actual_hot','actual_cold','actual_lattice_hot','actual_density_zero',
    'negative_Cv','zero_volume','bad_band','bad_reference','bad_bounds','out_of_range_component'])
def test_invalid_actual_or_structural_state_rejected_atomically(damage):
    cfg,old=coordinate_case(310000);f=list(old.anchor.frame)
    if damage=='actual_hot':old=replace(old,electron_energy_density_change=(*old.electron_energy_density_change,'1e8'))
    if damage=='actual_cold':old=replace(old,electron_energy_density_change=(*old.electron_energy_density_change,'-1e8'))
    if damage=='actual_lattice_hot':f.append('1e6')
    if damage=='actual_density_zero':old=replace(old,electron_density_change=('-1e25',))
    if damage=='negative_Cv':f[3]='-1000'
    if damage=='zero_volume':f[4]='0'
    if damage=='bad_band':f[5]='1e1001'
    if damage=='bad_reference':f[2]='1'
    if damage=='bad_bounds':f[7]='701'
    if damage=='out_of_range_component':old=replace(old,hole_energy_density_change=(*old.hole_energy_density_change,'1e-4001'))
    old=replace(old,anchor=replace(old.anchor,frame=tuple(f)));before=asdict(old)
    with pytest.raises(ValueError):nonlinear(cfg,old,2e-14)
    with localcontext() as ctx:
        ctx.prec=10000
        with pytest.raises((ValueError,ArithmeticError)):_point(old,_Arithmetic())
    assert asdict(old)==before

@pytest.mark.parametrize('damage',['remove_compensation','new_lattice','new_energy','metadata','clock'])
def test_rehashed_saved_state_forgeries_rejected(damage):
    cfg,old=hot();new,r=nonlinear(cfg,old,2e-14);r=deepcopy(r)
    if damage=='remove_compensation':new=replace(new,electron_energy_density_change=())
    if damage=='new_lattice':new=replace(new,anchor=replace(new.anchor,frame=(*new.anchor.frame,'1e-300')))
    if damage=='new_energy':new=replace(new,electron_energy_density_change=(*new.electron_energy_density_change,'1e-300'))
    if damage=='metadata':r['complete_device_energy']=True
    if damage=='clock':new=replace(new,time_s=1.)
    from tcad.postprocess.boltzmann_affine_transport import _fingerprint
    r['new_sha256']=r['collision']['new_sha256']=_fingerprint(new)
    try:check=audit(cfg,old,new,r,dt_s=2e-14)
    except (ValueError,ArithmeticError):return
    assert not check['valid']

def test_native_and_production_disabled_for_saved_hot_state(monkeypatch):
    cfg,old=hot();new,r=nonlinear(cfg,old,2e-14);r.pop('independent_audit');r['collision'].pop('independent_audit')
    import tcad.core._bindings as native
    import tcad.solver.boltzmann_affine_powerlaw as pp
    import tcad.solver.boltzmann_affine_collision as pc
    from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw
    def deny(*a,**kw):raise AssertionError('native or production call in independent hot-state audit')
    for name in dir(native):
        if name.startswith(('native_','three_temperature_')) and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    monkeypatch.setattr(pp,'advance_mb_affine_powerlaw',deny);monkeypatch.setattr(pc,'advance_mb_affine_collision',deny);monkeypatch.setattr(EnergyRelaxationPowerLaw,'evaluate',deny)
    assert audit(cfg,old,new,r,dt_s=2e-14)['valid']
