from copy import deepcopy
from dataclasses import replace
from decimal import Decimal,localcontext
import pytest
from tests.test_mb_particle_energy import make
from tcad.solver.boltzmann_particle_energy import expand_mb_relaxation_state as expand,update_mb_particle_energy as update
from tcad.solver.boltzmann_expanded_collision import advance_mb_expanded_collision as advance
from tcad.postprocess.boltzmann_expanded_collision import audit_mb_expanded_collision as audit


@pytest.mark.parametrize('a,c',[(0.,0.),(.6,-.2),(-20000.,20000.),(20000.,-20000.),(-2000.,0.)])
def test_closed_expanded_three_temperature_trajectory_and_saved_audit(a,c,monkeypatch):
    cfg,state=make(a,c);old=expand(cfg,state)
    for dt in (2e-14,5e-14,9e-14):
        previous=old
        new,report=advance(cfg,old,dt)
        assert report['independent_audit']['valid'] and new.time_s==old.time_s+dt
        old=new
    import tcad.core._bindings as native
    def deny(*a,**kw):raise AssertionError('native physics used in saved audit')
    for name in dir(native):
        if name.startswith('native_') and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    assert audit(cfg,previous,new,report,dt_s=dt,impulses_J=[0.,0.,0.],energy_atol_J=1e-27)['valid']


@pytest.mark.parametrize('tail',['1e-300','-1e-300','1e-1863','-1e-1863'])
def test_finite_background_lineages_do_not_hide_tiny_carrier_response(tail):
    cfg,s=make();old=expand(cfg,s)
    old=replace(old,electron_excess=(*old.electron_excess,tail),hole_excess=(*old.hole_excess,tail))
    new,r=advance(cfg,old,2e-14)
    assert r['independent_audit']['valid']
    row=r['lineage_groups'][1]
    assert all(Decimal(x)!=0 for x in row['exchange_densities'])
    assert any(abs(Decimal(x))<Decimal('1e-250') and Decimal(x)!=0 for x in new.electron_excess)
    assert all(x['valid'] for x in r['independent_audit']['lineage_checks'])


def test_near_unity_retention_keeps_microscopic_losses_below_finite_input_ulp():
    cfg,s=make(2000.,0.);old=expand(cfg,s)
    new,r=advance(cfg,old,2e-14)
    row=r['lineage_groups'][0]
    assert len(row['electron_excess'])==4 and row['electron_excess'][0]==old.electron_excess[0]
    assert Decimal(row['exchange_densities'][0])!=0
    with localcontext() as ctx:
        ctx.prec=4000
        loss=sum(map(Decimal,row['electron_excess']))-Decimal(old.electron_excess[0])
        assert loss!=0 and abs(loss)<Decimal('1e-300')
    assert r['independent_audit']['valid']


@pytest.mark.parametrize('q',[(2e-19,-1e-19,3e-19),(1e-300,-1e-300,1e-300),(0.,0.,0.)])
def test_independent_carrier_and_lattice_sources(q):
    cfg,s=make();old=expand(cfg,s);new,r=advance(cfg,old,2e-14,impulses_J=q)
    assert r['independent_audit']['valid']
    assert audit(cfg,old,new,r,dt_s=2e-14,impulses_J=q,energy_atol_J=1e-27)['valid']


def test_density_and_band_transaction_then_expanded_collision():
    cfg,s=make(.6,-.2);old=expand(cfg,s)
    old,_=update(old,[1.01e25,.99e25],[1e-22,-1e-22])
    new,r=advance(cfg,old,2e-14)
    assert new.frame[:9]==old.frame[:9] and r['independent_audit']['valid']


@pytest.mark.parametrize('damage',['micro_lineage','micro_loss','compensated_parts','state','lattice','clock','source','metadata','view'])
def test_coherent_and_incoherent_saved_forgeries_rejected(damage):
    cfg,s=make(2000.,0.);old=expand(cfg,s)
    old=replace(old,electron_excess=(*old.electron_excess,'1e-1863'))
    new,r=advance(cfg,old,2e-14);r=deepcopy(r)
    if damage=='micro_lineage':
        row=r['lineage_groups'][1]
        row['lattice_increment_density']='0';row['exchange_densities']=['0','0']
        row['electron_excess']=['0']*4;row['hole_excess']=['0']*4
    if damage=='micro_loss':r['lineage_groups'][0]['electron_excess'][-1]='0'
    if damage=='compensated_parts':
        with localcontext() as ctx:
            ctx.prec=10000
            parts=r['lineage_groups'][0]['electron_excess'];baseline=Decimal(parts[1])+Decimal(parts[2])
            parts[1]='1e1000';parts[2]=str(baseline-Decimal('1e1000'))
    if damage in ('micro_lineage','micro_loss','compensated_parts'):
        def flatten(field):return tuple(x for row in r['lineage_groups'] for x in row[field] if Decimal(x)!=0) or ('0',)
        lattice=tuple(row['lattice_increment_density'] for row in r['lineage_groups'] if Decimal(row['lattice_increment_density'])!=0)
        r['lattice_increment_expansion']=list(lattice)
        new=replace(new,frame=(*old.frame,*lattice),electron_excess=flatten('electron_excess'),hole_excess=flatten('hole_excess'))
    if damage=='state':new=replace(new,electron_excess=(*new.electron_excess,'1e-300'))
    if damage=='lattice':new=replace(new,frame=(*new.frame,'1e-300'))
    if damage=='clock':new=replace(new,time_s=1.)
    if damage=='source':r['impulses_J'][0]='1e-20'
    if damage=='metadata':r['complete_device_energy']=True
    if damage=='view':r['temperatures_K'][1]='777'
    try:result=audit(cfg,old,new,r,dt_s=2e-14,impulses_J=(0.,0.,0.),energy_atol_J=1e-27)
    except ValueError:return
    assert not result['valid']


def test_saved_audit_has_no_native_or_production_law_calls(monkeypatch):
    cfg,s=make(.6,-.2);old=expand(cfg,s);new,r=advance(cfg,old,2e-14)
    import tcad.core._bindings as native
    from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw
    def deny(*a,**kw):raise AssertionError('production physics used')
    for name in dir(native):
        if name.startswith('native_') and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    monkeypatch.setattr(EnergyRelaxationPowerLaw,'evaluate',deny)
    assert audit(cfg,old,new,r,dt_s=2e-14,impulses_J=(0.,0.,0.),energy_atol_J=1e-27)['valid']


@pytest.mark.parametrize('dt,q,budget,maximum',[(0.,(0.,0.,0.),1e-27,256),
    (2e-14,(1.,0.,0.),1e-27,256),(2e-14,(0.,0.,0.),0.,256),(2e-14,(0.,0.,0.),1e-27,1)])
def test_failed_collision_is_atomic(dt,q,budget,maximum):
    cfg,s=make();old=expand(cfg,s);before=deepcopy(old)
    with pytest.raises((ValueError,RuntimeError)):advance(cfg,old,dt,impulses_J=q,energy_atol_J=budget,max_nfev=maximum)
    assert old==before


def test_output_budget_exhaustion_is_atomic():
    cfg,s=make();old=expand(cfg,s);old=replace(old,frame=(*old.frame,*('0',)*246))
    with pytest.raises(ValueError):advance(cfg,old,2e-14)


def test_configuration_frame_mismatch_rejected():
    cfg,s=make();old=expand(cfg,s);old=replace(old,frame=(*old.frame[:3],'1001',*old.frame[4:]))
    with pytest.raises(ValueError):advance(cfg,old,2e-14)


def test_zero_equilibrium_has_exact_zero_budget_and_no_lattice_history_growth():
    cfg,s=make();old=replace(expand(cfg,s),electron_excess=('0',),hole_excess=('0',))
    new,r=advance(cfg,old,2e-14)
    assert new.frame==old.frame and new.electron_excess==new.hole_excess==('0',)
    assert Decimal(r['independent_audit']['global_budget_J'])==0 and r['independent_audit']['valid']


def test_unrepresentable_stiff_tail_rejected_without_clipping():
    cfg,s=make(-20000.,0.);old=expand(cfg,s);before=deepcopy(old)
    with pytest.raises(ValueError):advance(cfg,old,2e-14)
    assert old==before


def test_boolean_evaluation_budget_rejected():
    cfg,s=make();old=expand(cfg,s)
    with pytest.raises(ValueError):advance(cfg,old,2e-14,max_nfev=True)


def test_driven_sequence_packs_lattice_without_losing_native_binary_energy():
    cfg,s=make();old=expand(cfg,s)
    for dt in (2e-14,5e-14,9e-14):
        new,r=advance(cfg,old,dt,impulses_J=(2e-19,-1e-19,3e-19))
        assert r['independent_audit']['lattice_packing_binary_exact']
        assert len(new.frame)<256
        assert new.frame[:len(old.frame)]==old.frame
        assert len(r['lattice_increment_expansion'])<len(r['lineage_groups'])
        old=new


def test_coherent_packed_microscopic_lattice_deletion_is_rejected():
    cfg,s=make(2000.,0.);old=expand(cfg,s)
    old=replace(old,electron_excess=(*old.electron_excess,'1e-1863'))
    new,r=advance(cfg,old,2e-14);r=deepcopy(r)
    packed=r['lattice_increment_expansion']
    index=min(range(len(packed)),key=lambda i:abs(Decimal(packed[i])))
    assert 0<abs(Decimal(packed[index]))<Decimal('1e-300')
    del packed[index]
    new=replace(new,frame=(*old.frame,*packed))
    result=audit(cfg,old,new,r,dt_s=2e-14,impulses_J=(0.,0.,0.),energy_atol_J=1e-27)
    assert not result['valid'] and not result['lattice_packing_binary_exact']
