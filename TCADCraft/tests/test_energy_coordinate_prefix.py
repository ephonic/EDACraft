from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from tcad.solver.device_energy_coordinate_transport import DeviceEnergyCoordinateTransport as Device
from tcad.postprocess.energy_coordinate_prefix import audit_energy_coordinate_prefixes as audit, EnergyCoordinatePrefixError
import tcad.postprocess.energy_coordinate_prefix as prefix
from docs.validation.fd_source_prefixes_20261025.cases import control,BUDGET,DT,KINDS


@pytest.fixture(scope='module')
def paths():
    result={}
    for kind in KINDS:
        model,thermal=control(kind);device=Device(model,thermal);initial=device.state;records=[]
        for i in range(2):
            new,report=device.advance(DT,**BUDGET)
            records.append(dict(index=i,new=new,report=report))
        result[kind]=(model,initial,records,device.state)
    return result


def checked(path,**kw):
    model,old,rows,final=path
    return audit(model,old,rows,final_state=final,steps=len(rows),checkpoint_stride=1,**BUDGET,**kw)


@pytest.mark.parametrize('kind',KINDS)
def test_every_native_substep_closes_cells_field_and_sources(paths,kind):
    model,old,rows,final=paths[kind];r=checked(paths[kind])
    assert r['valid'] and r['accepted_native_substeps']==r['independently_reaudited_substeps']==2
    assert len(r['checkpoints'])==2 and r['audited_cell_substeps']==2*model.nc
    assert r['all_local_matter_and_particle_prefixes_closed'] and r['all_global_field_energy_and_charge_prefixes_closed']
    assert r['cumulative_budget_policy']=='fixed_cap_at_every_native_substep'
    assert not r['complete_device_energy'] and not r['general_complex_physics_closed']
    if kind=='absorption':assert r['final']['photon_energy_J']<0
    else:
        assert r['final']['photon_energy_J']>0 and r['final']['generation_energy_J']>0
        assert min(r['final']['generated_pairs'])>0
    if kind=='contact_sources':
        assert r['final']['endpoint_energy_increments_J']['electrostatic']!=0
        assert r['final']['source_work_J']!=0
    if kind=='stiff_sources':
        assert model.relaxation_laws[0].lattice_temperature_exponent==-20000
        assert model.relaxation_laws[0].density_exponent==20000
        assert all(np.longdouble(v)!=0 for v in final.excess_J_m3)


def test_intermediate_local_failure_cannot_be_hidden_by_later_opposite_fault(paths,monkeypatch):
    path=paths['contact_sources'];real=prefix._ports
    def faulty(model,old,new,charge):
        boundary,cells,work=real(model,old,new,charge)
        sign=1 if old.thermal.time_s==0 else -1
        cells['electrons']=cells['electrons']+sign*np.array([2e-26,-2e-26])
        return boundary,cells,work
    # A whole-path final check cancels both signs. The new audit must stop at
    # the first prefix, before the compensating second row can be requested.
    model,old,rows,final=path
    a=faulty(model,old,rows[0]['new'],BUDGET['charge_atol_C'])[1]['electrons']
    b=faulty(model,rows[0]['new'],final,BUDGET['charge_atol_C'])[1]['electrons']
    c=real(model,old,rows[0]['new'],BUDGET['charge_atol_C'])[1]['electrons']
    d=real(model,rows[0]['new'],final,BUDGET['charge_atol_C'])[1]['electrons']
    arithmetic_bound=8*np.finfo(np.longdouble).eps*max(np.max(abs(v)) for v in (a,b,c,d))
    np.testing.assert_allclose(a+b,c+d,rtol=0,atol=arithmetic_bound)
    assert arithmetic_bound<BUDGET['energy_atol_J']*1e-6
    monkeypatch.setattr(prefix,'_ports',faulty);visited=[]
    def stream():
        for row in rows:visited.append(row['index']);yield row
    with pytest.raises(EnergyCoordinatePrefixError) as failure:
        audit(model,old,stream(),final_state=final,steps=2,**BUDGET)
    assert visited==[0] and failure.value.diagnostic['step']==1 and not failure.value.diagnostic['valid']


@pytest.mark.parametrize('damage',['missing','extra','index','state_energy','field','photon','generation','scope'])
def test_forged_or_incomplete_evidence_is_rejected(paths,damage):
    model,old,rows,final=deepcopy(paths['contact_sources'])
    if damage=='missing':rows.pop()
    elif damage=='extra':rows.append(deepcopy(rows[-1]));rows[-1]['index']=2
    elif damage=='index':rows[0]['index']=True
    elif damage=='state_energy':rows[0]['new']=replace(rows[0]['new'],excess_J_m3=('0',)*4)
    elif damage=='field':rows[0]['report']['raw']['local_cells'][14]='1'
    elif damage=='photon':rows[0]['report']['raw']['transport']['radiative_moments'][0][2]*=2
    elif damage=='generation':model.pair_generation_rate_m3_s*=2
    else:rows[0]['report']['complete_device_energy']=True
    with pytest.raises((ValueError,ArithmeticError)):
        audit(model,old,rows,final_state=final,steps=2,**BUDGET)


def test_producer_audit_claims_do_not_supply_prefix_evidence(paths):
    model,old,rows,final=deepcopy(paths['stiff_sources'])
    for row in rows:row['report']['independent_audit']={'valid':True,'source_work_J':1e99}
    assert audit(model,old,rows,final_state=final,steps=2,**BUDGET)['valid']


def test_iterator_cannot_change_owned_model_endpoints_or_previous_row(paths):
    model,old,rows,final=deepcopy(paths['contact_sources'])
    def stream():
        model.pair_generation_rate_m3_s*=3
        yield rows[0]
        rows[0]['report']['raw']['local_cells'][14]='100'
        yield rows[1]
    assert audit(model,old,stream(),final_state=final,steps=2,**BUDGET)['valid']


@pytest.mark.parametrize('option', ['cumulative_energy_atol_J','cumulative_particle_atol'])
def test_tight_cumulative_cap_is_checked_at_first_failing_prefix(paths,option):
    with pytest.raises(EnergyCoordinatePrefixError): checked(paths['contact_sources'],**{option:1e-60})


@pytest.mark.parametrize('options',[{'steps':True},{'steps':16385},{'checkpoint_stride':0},
    {'cumulative_energy_atol_J':1e-26},{'cumulative_particle_atol':1e-8}])
def test_invalid_prefix_controls_do_not_invoke_iterator(paths,options):
    model,old,rows,final=paths['stiff_sources'];kw=dict(steps=2,**BUDGET);kw.update(options)
    def stream():
        raise AssertionError('iterator must not run')
        yield
    with pytest.raises(ValueError):audit(model,old,stream(),final_state=final,**kw)


def test_native_physics_calls_are_not_used_by_replay(paths,monkeypatch):
    import tcad.core._bindings as native
    def deny(*a,**kw):raise AssertionError('native physics forbidden')
    for name in dir(native):
        if name.startswith('native_') and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    assert checked(paths['contact_sources'])['valid']
