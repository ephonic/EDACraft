"""General FD combination prefixes, fixed caps and independent replay."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from test_temperature_dependent_bands import band_case
from test_varshni_temperature_bands import configure
from test_three_temperature import BUDGET
from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw as Law
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.postprocess.three_temperature_prefix import (
    audit_three_temperature_prefixes as audit, ThreeTemperaturePrefixError)


@pytest.fixture(scope='module', params=[False, True])
def accepted(request):
    model, initial = band_case(complex=True, contacts=request.param, count=2 if request.param else 1)
    configure(model)
    model.relaxation_laws=(Law(300,1e25,-.4,.2,.3), Law(300,1e25,.25,-.15,-.2))
    device=DeviceThreeTemperature(model,initial)
    rows=[]
    for index in range(3):
        new, report=device.advance(1e-15,**BUDGET)
        rows.append(dict(index=index,new=new,report=report))
    return model,initial,rows


def run(fixture, rows=None, **kwargs):
    model, initial, source=fixture
    rows=source if rows is None else rows
    return audit(model,initial,rows,final_state=source[-1]['new'],steps=len(source),**BUDGET,**kwargs)


def test_all_existing_sources_nonlinear_band_and_nonzero_b_prefixes(accepted):
    model,initial,rows=accepted
    result=run(accepted,checkpoint_stride=1)
    assert result['valid'] and len(result['checkpoints'])==3
    assert result['independently_reaudited_substeps']==3
    assert result['audited_cell_substeps']==3*model.nc
    assert result['maximum_prefix_errors']['energy_J']<=1e-27
    assert not result['general_complex_physics_closed'] and not result['physical_validated']
    for row in rows:
        r=row['report']
        assert r['dynamic_trap_device_coupled'] and r['radiative_device_coupled'] and r['auger_device_coupled']
        for key in ('cell_generated_pairs','cell_intercarrier_exchange_J','cell_band_work_from_lattice_J'):
            assert key in r
    assert model.relaxation_laws[0].carrier_temperature_exponent!=0


@pytest.mark.parametrize('damage',['index','missing','extra','endpoint','trap','photon','band','auger'])
def test_corrupt_source_coverage_and_endpoint_rejected(accepted,damage):
    rows=deepcopy(accepted[2])
    if damage=='index':rows[0]['index']=True
    elif damage=='missing':rows.pop()
    elif damage=='extra':rows.append(deepcopy(rows[-1]))
    elif damage=='endpoint':rows[-1]['new']=replace(rows[-1]['new'],time_s=1.)
    elif damage=='trap':rows[0]['report']['cell_trap_lattice_heat_J'][0]+=1e-18
    elif damage=='photon':rows[0]['report']['outward_energy_J']['photons']+=1e-18
    elif damage=='band':rows[0]['report']['cell_band_work_from_lattice_J']['electrons'][0]+=1e-18
    else:rows[0]['report']['cell_auger_carrier_energy_added_J']['holes'][0]+=1e-18
    with pytest.raises(ValueError):run(accepted,rows)


def test_producer_attached_audit_is_not_evidence(accepted):
    rows=deepcopy(accepted[2])
    for row in rows:row['report']['independent_audit']=dict(valid=False,poison=object())
    assert run(accepted,rows)==run(accepted)


def test_first_failed_prefix_stops_before_compensating_record(accepted,monkeypatch):
    import tcad.postprocess.three_temperature_prefix as module
    original=module.audit_three_temperature_energy
    def injected(*args,**kwargs):
        checked=original(*args,**kwargs)
        checked['independently_reconstructed_cell_ledger']['transport_energy_J']['electrons'][0]+=2e-27
        return checked
    monkeypatch.setattr(module,'audit_three_temperature_energy',injected)
    def source():
        yield accepted[2][0]
        raise AssertionError('must reject before requesting a compensating next row')
    with pytest.raises(ThreeTemperaturePrefixError) as error:run(accepted,source())
    assert error.value.diagnostic['step']==1 and not error.value.diagnostic['valid']


@pytest.mark.parametrize('control',[dict(steps=True),dict(energy_atol_J=2e-27),
    dict(cumulative_energy_atol_J=2e-27),dict(cumulative_charge_atol_C=4e-28),dict(checkpoint_stride=0)])
def test_invalid_controls_never_request_iterator(accepted,control):
    def source():
        raise AssertionError('invalid controls requested iterator')
        yield
    model,initial,rows=accepted
    options=dict(BUDGET,steps=len(rows));options.update(control)
    with pytest.raises(ValueError):audit(model,initial,source(),final_state=rows[-1]['new'],**options)


def test_tighter_cumulative_budget_and_iterator_ownership(accepted):
    expected=run(accepted)
    model,initial,rows=deepcopy(accepted)
    def source():
        model.tau_n[:]=1e-3
        for row in rows:
            yield row
            row['report']['energy_increments_J']['electrons']=1e-4
    actual=audit(model,initial,source(),final_state=rows[-1]['new'],steps=len(rows),**BUDGET)
    assert actual==expected
    with pytest.raises(ThreeTemperaturePrefixError):run(accepted,cumulative_energy_atol_J=1e-40)


def test_replay_calls_no_native_physics_or_production_step(accepted,monkeypatch):
    import tcad.core._bindings as native
    def denied(*args,**kwargs):raise AssertionError('production physics called during replay')
    expected=run(accepted)
    for name in dir(native):
        if name.startswith('native_') and callable(getattr(native,name)):monkeypatch.setattr(native,name,denied)
    monkeypatch.setattr(DeviceThreeTemperature,'advance',denied)
    monkeypatch.setattr(Law,'evaluate',denied)
    for name in ('_poisson','carrier_reservoirs','split_face_transport','energies','conduction'):
        monkeypatch.setattr(accepted[0],name,denied)
    assert run(accepted)==expected
