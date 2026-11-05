"""Local energy elimination: analytic moments, actual device replay and tiny e."""
from copy import deepcopy
from decimal import Decimal,localcontext
import numpy as np
import pytest
from tcad.physics.excess_transport_local import assemble_excess_transport_local as assemble
from tcad.postprocess.excess_transport_local import audit_excess_transport_local as audit
from test_three_temperature import case,BUDGET

D=Decimal


def manufactured(a=-20000,c=20000,balanced=True):
    """Prescribed moment fixture, not a solved device or measured material."""
    cells=[]
    for i in range(2):
        Tl=('303','303.2')[i] if a<0 else ('297','296.8')[i] if a>0 else ('301','302')[i]
        cells.append(list(map(str,('1e25','1e25','300',('1.001e25','0.999e25')[i],
            ('0.998e25','1.002e25')[i],Tl,'50000','51000','2000','48000','49000','-1000',
            ('1e-21','2e-21')[i],'1000',('0.001','-0.001')[i],('0.002','-0.002')[i],
            ('0.01','0.03')[i],'1e-13','150','5e24',a,c,'4e-13','150','5e24',a,c,
            '0','0','1e-19','-2e-19','3e-19','2e-20','-3e-20'))))
    faces=[list(map(str,(0,1,'1e15','-2e15','2e-5','-1e-5','0.0001','-0.0002','1e-14','5e-8','1e-7',0,0))),
           list(map(str,(0,-1,'3e14','-1e14','1e-6','-2e-6','0.003','0.004','1e-14','5e-8',0,310,1)))]
    dt='2e-14'
    if balanced:
        # Choose signed imposed reservoir impulses/counts from a separate
        # Decimal replay, not from native reported residuals.
        probe=audit(cells,faces,dt,assemble(cells,faces,dt))['reference_cells']
        with localcontext() as ctx:
            ctx.prec=90
            for row,ref in zip(cells,probe):
                row[27]=str(D(row[27])+D(ref['particle_n']));row[28]=str(D(row[28])+D(ref['particle_p']))
                row[31]=str(D(row[31])+D(ref['residual_l_J']))
    return cells,faces,dt


@pytest.mark.parametrize('a,c',[(-20000,20000),(20000,-20000),(0,0),(-.4,.3)])
def test_nonzero_oriented_flux_density_change_work_bath_and_sources(a,c):
    cells,faces,dt=manufactured(a,c)
    r=assemble(cells,faces,dt);v=audit(cells,faces,dt,r)
    assert v['valid'] and v['local_residuals_closed'],v
    assert all(D(row['work_n_J'])!=0 and D(row['work_p_J'])!=0 for row in r['cells'])
    assert all(D(row['excess_n_J_m3'])!=0 and D(row['excess_p_J_m3'])!=0 for row in r['cells'])
    if abs(a)>10000:
        assert all(abs(D(row['excess_n_J_m3']))<D('1e-50') for row in r['cells'])
    assert all(D(v)!=0 for v in r['heat_flux_W'])
    assert not r['device_state_advanced'] and not r['nonlinear_face_coupling_solved']
    assert not r['complete_device_energy'] and not r['physical_validated']


def test_face_reorientation_preserves_each_cell_and_reverses_internal_fourier():
    cells,faces,dt=manufactured();original=assemble(cells,faces,dt)
    reversed_faces=deepcopy(faces);row=reversed_faces[0];row[0],row[1]=row[1],row[0]
    row[9],row[10]=row[10],row[9]
    for k in (2,3,4,5):row[k]=str(-D(row[k]))
    reverse=assemble(cells,reversed_faces,dt)
    assert reverse['cells']==original['cells']
    assert D(reverse['heat_flux_W'][0])==D(original['heat_flux_W'][0]).copy_negate()
    assert reverse['heat_flux_W'][1]==original['heat_flux_W'][1]
    assert audit(cells,reversed_faces,dt,reverse)['local_residuals_closed']


@pytest.mark.parametrize('damage',['excess_n_J_m3','excess_p_J_m3','exchange_n_J','exchange_p_J',
    'work_n_J','storage_n_J','storage_l_J','residual_l_J','particle_n','tau_n_s','retained_n',
    'face','scope','complete','device','coupling'])
def test_independent_replay_rejects_corruption_including_erased_tiny_excess(damage):
    cells,faces,dt=manufactured();r=assemble(cells,faces,dt)
    if damage=='face':r['heat_flux_W'][0]='0'
    elif damage=='scope':r['scope']='complete_device'
    elif damage in ('complete','device','coupling'):
        r[{'complete':'complete_device_energy','device':'device_state_advanced','coupling':'nonlinear_face_coupling_solved'}[damage]]=True
    else:
        r['cells'][0][damage]=('1e-10' if damage in ('residual_l_J','particle_n') else '0')
    assert not audit(cells,faces,dt,r)['valid']


def test_unclosed_candidate_is_a_valid_assembly_without_an_acceptance_claim():
    cells,faces,dt=manufactured(balanced=False);r=assemble(cells,faces,dt);v=audit(cells,faces,dt,r)
    assert v['valid'] and not v['local_residuals_closed']


def test_independent_replay_uses_no_native_or_production_law(monkeypatch):
    cells,faces,dt=manufactured();r=assemble(cells,faces,dt)
    import tcad.core._bindings as native
    import tcad.physics.excess_transport_local as production
    from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw
    def deny(*a,**k):raise AssertionError('production called by independent replay')
    for name in dir(native):
        if name.startswith('native_') and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    monkeypatch.setattr(production,'assemble_excess_transport_local',deny)
    monkeypatch.setattr(EnergyRelaxationPowerLaw,'evaluate',deny)
    assert audit(cells,faces,dt,r)['local_residuals_closed']


def actual_general_replay(contacts=False):
    """Actual existing accepted nonlinear device, not manufactured forcing."""
    model,old=case(contacts=contacts,voltage=.002 if contacts else 0.)
    dt=2e-13;new,report=model.step(old,dt,**BUDGET)
    cache,a,stats,history=model._native_step(old,dt,**BUDGET,max_nfev=600)
    b=cache['poisson']
    states=[model.carrier_reservoirs(st.n_m3,st.p_m3,st.electron_temperature_K,
            st.hole_temperature_K,st.temperature_K) for st in (old,new)]
    eq=[model.carrier_reservoirs(st.n_m3,st.p_m3,st.temperature_K,st.temperature_K,
        st.temperature_K) for st in (old,new)]
    def text(value):return str(np.longdouble(value))
    cells=[]
    for i in range(model.nc):
        values=list(map(text,(old.n_m3[i],old.p_m3[i],old.temperature_K[i],new.n_m3[i],new.p_m3[i],new.temperature_K[i])))
        for s in ('electrons','holes'):
            e0=D(text(states[0][s][i]['energy_density_J_m3']))-D(text(eq[0][s][i]['energy_density_J_m3']))
            values.extend((text(eq[0][s][i]['energy_density_J_m3']),text(eq[1][s][i]['energy_density_J_m3']),str(e0)))
        values.extend(map(text,(model.vol[i],model.capacity[i],a['cell_potential_V'][i],b['cell_potential_V'][i],model.conductivity[i])))
        for tau in (model.tau_n[i],model.tau_p[i]):values.extend(map(text,(tau,300,1e25,0,0)))
        values.extend(['0']*7);cells.append(values)
    faces=[]
    for f,face in enumerate(model.mesh.faces):
        faces.append(list(map(text,(face.owner,face.neighbor,cache['rates']['electrons'][f],cache['rates']['holes'][f],
            cache['energies']['electrons'][f],cache['energies']['holes'][f],a['face_potential_V'][f],b['face_potential_V'][f],
            model.area[f],model.do[f],model.dn[f],model.bath.get(f,0),int(f in model.bath)))))
    return cells,faces,text(dt),new,report,model


@pytest.mark.parametrize('contacts',[False,True])
def test_matches_existing_actual_density_changing_device_transport(contacts):
    cells,faces,dt,new,report,model=actual_general_replay(contacts)
    r=assemble(cells,faces,dt);v=audit(cells,faces,dt,r)
    assert v['valid'] and v['local_residuals_closed'],v
    assert any(abs(D(row[3])/D(row[0])-1)>D('1e-5') for row in cells)
    assert any(D(row[2])!=0 and D(row[3])!=0 and D(row[4])!=0 and D(row[5])!=0 for row in faces)
    for i,row in enumerate(r['cells']):
        for suffix,label in (('n','electrons'),('p','holes')):
            assert abs(float(row['exchange_'+suffix+'_J'])-report['cell_exchange_J'][label][i])<1e-27


def test_original_negative_a_isolated_root_replays_without_zeroing_excess():
    from test_isolated_relaxation import solver
    device,model,old=solver();initial=device.state;new,report=device.advance(2e-14,**BUDGET)
    config=device.configuration
    from tcad.core._bindings import native_fermi_reservoir_raw
    def energy(s,t):
        return str(native_fermi_reservoir_raw(['1e25',t,'0'],config.packed_valleys()[s])[1])
    values=['1e25','1e25',initial.lattice_temperature_K,'1e25','1e25',new.lattice_temperature_K]
    for s,e0 in enumerate((initial.electron_excess_energy_J_m3,initial.hole_excess_energy_J_m3)):
        values.extend((energy(s,initial.lattice_temperature_K),energy(s,new.lattice_temperature_K),e0))
    values.extend(['1e-21','1000','0','0','.001'])
    for tau in ('1e-13','4e-13'):values.extend((tau,'150','5e24','-20000','20000'))
    values.extend(['0']*7)
    r=assemble([values],[],'2e-14');v=audit([values],[],'2e-14',r)
    assert v['valid'] and v['local_residuals_closed'],v
    assert D('1e-84')<abs(D(r['cells'][0]['excess_n_J_m3']))<D('1e-77')
    assert abs(D(r['cells'][0]['exchange_n_J'])-D(report['exchange_J'][0]))<D('1e-30')
    # Rounded absolute energies lose this coordinate completely.
    eq=D(values[7]);assert float(eq+D(r['cells'][0]['excess_n_J_m3']))==float(eq)


@pytest.mark.parametrize('damage',['density','volume','cv','conductivity','tau','Tref','nref',
    'nan','owner','neighbor','self','area','distance','bath','zero_dt','underflow_tau'])
def test_native_rejects_invalid_input(damage):
    cells,faces,dt=manufactured()
    indices={'density':3,'volume':12,'cv':13,'conductivity':16,'tau':17,'Tref':18,'nref':19}
    if damage in indices:cells[0][indices[damage]]='0'
    elif damage=='nan':cells[0][8]='nan'
    elif damage=='owner':faces[0][0]='0.5'
    elif damage=='neighbor':faces[0][1]='2'
    elif damage=='self':faces[0][1]='0'
    elif damage=='area':faces[0][8]='-1'
    elif damage=='distance':faces[0][10]='0'
    elif damage=='bath':faces[0][12]='1'
    elif damage=='zero_dt':dt='0'
    else:cells[0][20]='-200000'
    with pytest.raises(ValueError):assemble(cells,faces,dt)


@pytest.mark.parametrize('sign',[-1,1])
def test_deep_weights_preserve_both_subnormal_tau_and_tiny_lost_exchange(sign):
    cells,_,dt=manufactured(balanced=False);cells=cells[:1];row=cells[0]
    row[3]=row[4]='1e25';row[5]='310.9'
    row[20]=row[25]=str(sign*20000);row[21]=row[26]=str(-sign*20000)
    row[27:34]=['0']*7
    r=assemble(cells,[],dt);v=audit(cells,[],dt,r)
    assert v['valid'],v
    if sign<0:
        assert 0<float(r['cells'][0]['tau_n_s'])<np.finfo(float).tiny
        assert 0<abs(D(r['cells'][0]['excess_n_J_m3']))<D('1e-290')
        field='excess_n_J_m3'
    else:
        assert D(r['cells'][0]['retained_n'])==1
        assert 0<abs(D(r['cells'][0]['exchange_n_J']))<D('1e-320')
        assert float(r['cells'][0]['exchange_n_J'])==0
        field='exchange_n_J'
    r['cells'][0][field]='0'
    assert not audit(cells,[],dt,r)['valid']
