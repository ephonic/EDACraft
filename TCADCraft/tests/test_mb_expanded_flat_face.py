from copy import deepcopy
from dataclasses import replace
from decimal import Decimal,localcontext
import pytest
from tests.test_mb_particle_energy import make
from tcad.solver.boltzmann_particle_energy import expand_mb_relaxation_state as expand,update_mb_particle_energy as update
from tcad.solver.boltzmann_expanded_collision import advance_mb_expanded_collision as collide
from tcad.physics.boltzmann_expanded_flat_face import expanded_mb_flat_face as face
from tcad.postprocess.boltzmann_expanded_flat_face import audit_expanded_mb_flat_face as audit

GEOMETRY=(1e-14,1e-8,2e-8,.1,.2)

def pair():
    cfg,s=make();a=expand(cfg,s)
    return cfg,a,replace(a,electron_excess=tuple(str(-Decimal(x)) for x in a.electron_excess),hole_excess=('0',))


@pytest.mark.parametrize('kind,g',[('bulk',GEOMETRY),('contact',(1e-14,1e-8,0.,.1,.2))])
def test_native_flat_moments_equal_independent_closed_form(kind,g):
    cfg,a,b=pair();r=face(a,b,g,face_kind=kind)
    assert r['independent_audit']['valid']
    assert all(x['monomials_binary_exact'] for x in r['independent_audit']['carriers'])
    with localcontext() as ctx:
        ctx.prec=100
        kb=Decimal('1.380649e-23');q=Decimal('1.602176634e-19');G=Decimal.from_float(g[0])/(Decimal.from_float(g[1])/Decimal.from_float(g[3])+Decimal.from_float(g[2])/Decimal.from_float(g[4]))/q
        for k,field in enumerate(('electron_excess','hole_excess')):
            n=Decimal(a.frame[k]);Tl=Decimal(a.frame[2])+sum(map(Decimal,a.frame[9:]))/Decimal(a.frame[3])
            To=Tl+sum(map(Decimal,getattr(a,field)))/(Decimal('1.5')*kb*n)
            Tn=Tl+sum(map(Decimal,getattr(b,field)))/(Decimal('1.5')*kb*n)
            expected=[G*kb*n*(To-Tn),G*Decimal('2.5')*kb*kb*n*(To*To-Tn*Tn)]
            actual=[sum(map(Decimal,r['carriers'][k][key])) for key in ('number_expansion','energy_expansion')]
            assert all(abs(x-y)<Decimal('1e-28')*abs(y) for x,y in zip(actual,expected))


@pytest.mark.parametrize('tail',['1e-300','-1e-300','1e-1863','-1e-1863'])
def test_sub_temperature_resolution_difference_retains_particle_energy_and_quadratic_tail(tail):
    cfg,a,b=pair();b=replace(a,electron_excess=('0',),hole_excess=('0',))
    a=replace(b,electron_excess=(tail,),hole_excess=(tail,))
    r=face(a,b,GEOMETRY)
    for row in r['carriers']:
        assert sum(map(Decimal,row['number_expansion']))!=0
        assert any(x['kind']==5 and x['value'] for x in row['terms'])
        assert all(x!=0 for x in map(Decimal,row['number_expansion']))
    assert r['independent_audit']['valid']


@pytest.mark.parametrize('tail',['1e-300','1e-1863'])
def test_tiny_difference_inside_finite_carrier_background_is_not_collapsed(tail):
    cfg,a,b=pair();b=a;a=replace(a,electron_excess=(*a.electron_excess,tail))
    r=face(a,b,GEOMETRY)
    assert r['carriers'][0]['number_expansion'] and r['carriers'][0]['energy_expansion']
    assert r['carriers'][1]['number_expansion']==r['carriers'][1]['energy_expansion']==[]
    assert r['independent_audit']['valid']


@pytest.mark.parametrize('factor',[.9,1.1])
def test_density_changed_expanded_states_can_supply_flat_face_moments(factor):
    cfg,a,b=pair();b,_=update(a,[1e25*factor,1e25/factor],[0.,0.])
    r=face(a,b,GEOMETRY)
    assert r['independent_audit']['valid'] and any(t['kind']==6 for t in r['carriers'][0]['terms'])


def test_expanded_collision_output_supplies_face_without_scalar_adapter():
    cfg,a,b=pair();a,_=collide(cfg,a,2e-14)
    b=replace(a,electron_excess=(*a.electron_excess,'1e-1863'))
    r=face(a,b,GEOMETRY)
    assert r['independent_audit']['valid'] and r['carriers'][0]['number_expansion']


def test_direction_reversal_and_common_band_gauge():
    cfg,a,b=pair();r=face(a,b,GEOMETRY)
    reverse=face(b,a,(GEOMETRY[0],GEOMETRY[2],GEOMETRY[1],GEOMETRY[4],GEOMETRY[3]))
    shifted=[replace(x,frame=(*x.frame[:5],'1e-17','-1e-17',*x.frame[7:])) for x in (a,b)]
    gauge=face(*shifted,GEOMETRY)
    with localcontext() as ctx:
        ctx.prec=10000
        for k in range(2):
            N=sum(map(Decimal,r['carriers'][k]['number_expansion']));E=sum(map(Decimal,r['carriers'][k]['energy_expansion']))
            assert abs(N+sum(map(Decimal,reverse['carriers'][k]['number_expansion'])))<Decimal('1e-28')*abs(N)
            assert abs(E+sum(map(Decimal,reverse['carriers'][k]['energy_expansion'])))<Decimal('1e-28')*abs(E)
            shift=Decimal(shifted[0].frame[5+k]);shiftedE=sum(map(Decimal,gauge['carriers'][k]['energy_expansion']))
            assert abs(shiftedE-E-shift*N)<Decimal('1e-28')*max(abs(E),abs(shift*N))


def test_identical_state_zero_flux_and_zero_signal_budget():
    cfg,a,b=pair();r=face(a,a,GEOMETRY)
    assert all(x['number_expansion']==x['energy_expansion']==[] for x in r['carriers'])
    assert all(all(Decimal(x)==0 for x in row['budgets']) for row in r['independent_audit']['carriers'])


def test_finite_canceling_state_components_recover_microscopic_flux():
    cfg,a,b=pair();a=replace(a,electron_excess=('1e1000','-1e1000','1e-1863'),hole_excess=('0',))
    b=replace(a,electron_excess=('0',))
    r=face(a,b,GEOMETRY);assert r['independent_audit']['valid'] and r['carriers'][0]['number_expansion']


@pytest.mark.parametrize('damage',['micro_input','micro_product','parts','number','energy','coefficient','metadata','source','clock'])
def test_saved_face_forgery_rejected(damage):
    cfg,a,b=pair();b=a;a=replace(a,electron_excess=(*a.electron_excess,'1e-1863'))
    r=deepcopy(face(a,b,GEOMETRY));row=r['carriers'][0]
    if damage=='micro_input':row['normalization'][1]=[]
    if damage=='micro_product':
        target=next(t for t in row['terms'] if t['kind']==5 and t['value']);target['value']=[]
        row['energy_expansion']=[x for t in row['terms'] if t['kind']>=2 for x in t['value']]
    if damage=='parts':
        target=next(t for t in row['terms'] if t['value']);target['value']=['1e1000','-1e1000',*target['value']]
        row['number_expansion']=[x for t in row['terms'] if t['kind']<2 for x in t['value']]
    if damage=='number':row['number_expansion'].append('1e-300')
    if damage=='energy':row['energy_expansion'].append('1e-300')
    if damage=='coefficient':row['coefficients'][1]='0'
    if damage=='metadata':r['complete_device_energy']=True
    if damage=='source':r['geometry'][0]='1e-5'
    if damage=='clock':r['time_s']=1.
    try:result=audit(a,b,r,geometry=GEOMETRY)
    except ValueError:return
    assert not result['valid']


def test_saved_audit_does_not_call_native_physics_or_production_wrappers(monkeypatch):
    cfg,a,b=pair();r=face(a,b,GEOMETRY)
    import tcad.core._bindings as native
    def deny(*a,**kw):raise AssertionError('production physics used during independent audit')
    for name in dir(native):
        if name.startswith(('native_','three_temperature_')) and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    monkeypatch.setattr('tcad.physics.boltzmann_expanded_flat_face.expanded_mb_flat_face',deny)
    assert audit(a,b,r,geometry=GEOMETRY)['valid']


@pytest.mark.parametrize('damage',['lattice','band','time','temperature','geometry','kind','budget'])
def test_unsupported_inputs_reject_without_state_mutation(damage):
    cfg,a,b=pair();g=GEOMETRY;kw={};before=deepcopy(a)
    if damage=='lattice':b=replace(b,frame=(*b.frame[:9],'10001'))
    if damage=='band':b=replace(b,frame=(*b.frame[:5],'1e-22',*b.frame[6:]))
    if damage=='time':b=replace(b,time_s=1.)
    if damage=='temperature':b=replace(b,electron_excess=('1e20',))
    if damage=='geometry':g=(1e-14,0.,1e-8,.1,.2)
    if damage=='kind':kw['face_kind']='contact'
    if damage=='budget':kw['energy_atol_W']=0.
    with pytest.raises(ValueError):face(a,b,g,**kw)
    assert a==before


def test_unrepresentable_quadratic_tail_rejects_without_clipping():
    cfg,a,b=pair();a=replace(a,electron_excess=('1e-2500',),hole_excess=('0',));b=replace(a,electron_excess=('0',))
    with pytest.raises(ValueError):face(a,b,GEOMETRY)


@pytest.mark.parametrize('contact',[False,True])
def test_finite_face_moments_match_existing_native_spectral_quadrature(contact):
    from tcad.core._bindings import native_boltzmann_bulk_face_raw
    cfg,a,b=pair();g=list(GEOMETRY)
    if contact:g[2]=0.
    r=face(a,b,g,face_kind='contact' if contact else 'bulk')
    with localcontext() as ctx:
        ctx.prec=200
        kb=Decimal('1.380649e-23');Tl=Decimal(a.frame[2])+sum(map(Decimal,a.frame[9:]))/Decimal(a.frame[3])
        for k,field in enumerate(('electron_excess','hole_excess')):
            temperatures=[Tl+sum(map(Decimal,getattr(s,field)))/(Decimal('1.5')*kb*Decimal(s.frame[k])) for s in (a,b)]
            raw=native_boltzmann_bulk_face_raw([a.frame[k],str(temperatures[0]),a.frame[5+k],b.frame[k],str(temperatures[1]),b.frame[5+k]],
                ['0','0','0','-1',str(g[3]),str(g[4]),str(g[0]),str(g[1]),str(g[2]),'0'],['.3','.3','1','0'])
            actual=[sum(map(Decimal,r['carriers'][k][key])) for key in ('number_expansion','energy_expansion')]
            assert all(abs(x-Decimal(y))<=Decimal('2e-11')*abs(x) for x,y in zip(actual,raw[:2]))


def test_polynomial_component_budget_rejects_without_increasing_storage_limit():
    cfg,a,b=pair();values=tuple('1e'+str(-40*i) for i in range(40))
    a=replace(a,electron_excess=values,hole_excess=values);b=replace(a,electron_excess=('0',),hole_excess=('0',))
    with pytest.raises(ValueError,match='(term|component) budget'):face(a,b,GEOMETRY)


def test_coherent_deletion_of_product_low_part_fails_exact_binary_proof():
    cfg,a,b=pair();b=a;a=replace(a,electron_excess=(*a.electron_excess,'1e-1863'))
    r=deepcopy(face(a,b,GEOMETRY));row=r['carriers'][0]
    term=next(t for t in row['terms'] if t['kind']==1)
    assert len(term['value'])>=2
    index=min(range(len(term['value'])),key=lambda i:abs(Decimal(term['value'][i])))
    removed=term['value'].pop(index)
    row['terms']=[t for t in row['terms'] if not(t['kind']==2 and t['factors']==[removed])]
    row['number_expansion']=[x for t in row['terms'] if t['kind']<2 for x in t['value']]
    row['energy_expansion']=[x for t in row['terms'] if t['kind']>=2 for x in t['value']]
    result=audit(a,b,r,geometry=GEOMETRY)
    assert not result['valid']
    assert result['carriers'][0]['physical_flux_valid']
    assert not result['carriers'][0]['monomials_binary_exact']
