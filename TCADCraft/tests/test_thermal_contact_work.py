"""Independent contact-energy examples and actual nonisothermal exports."""
from copy import deepcopy
from pathlib import Path
import pytest
from tcad.postprocess.commercial_energy import (
    audit_sentaurus_contact_energy_flux,read_sentaurus_plt_rows,
)


def fixture():
    values={'a OuterVoltage':0.,'b OuterVoltage':2.,
            'a TotalCurrent':-3.,'b TotalCurrent':3.,
            'a eCurrent':-3.,'b eCurrent':3.,'a hCurrent':0.,'b hCurrent':0.,
            'a DisplacementCurrent':0.,'b DisplacementCurrent':0.,
            'a lHeatFlux':-2.,'b lHeatFlux':-2.,
            'a eHeatFlux':1.,'b eHeatFlux':-2.5,
            'a hHeatFlux':.25,'b hHeatFlux':-.75}
    bands={'a':{'conduction':0.,'valence':-1.},'b':{'conduction':-2.,'valence':-3.}}
    return values,bands


def audit(values=None,bands=None,**kwargs):
    original,edges=fixture()
    options=dict(contact_band_edges_eV=edges if bands is None else bands,
        electrodes=['a','b'],thermodes=['a','b'],power_atol_W=0.,current_atol_A=0.,power_rtol=0.,current_rtol=0.)
    options.update(kwargs)
    return audit_sentaurus_contact_energy_flux(original if values is None else values,**options)


def test_isothermal_contact_work_reduces_to_terminal_voltage_work():
    result=audit()
    assert result['valid'] and result['electrical_only_balance_valid']
    assert result['contact_band_work_W']==result['electrical_power_W']==6.
    assert result['contact_material_work_W']==0.
    assert not result['complete_device_energy'] and not result['physical_validated']


def test_zero_applied_voltage_can_have_nonzero_kinetic_energy_drive():
    values,bands=fixture();values['b OuterVoltage']=0.
    result=audit(values,bands)
    assert result['valid'] and not result['electrical_only_balance_valid']
    assert result['electrical_power_W']==0.
    assert result['contact_material_work_W']==result['outward_heat_power_W']==6.
    assert result['electrical_only_power_residual_W']==-6.


def test_common_energy_origin_preserves_gap_transfer_when_carrier_currents_convert():
    values,bands=fixture()
    values.update({'a eCurrent':-3.,'a hCurrent':1.,'a TotalCurrent':-2.,
                   'b eCurrent':2.,'b hCurrent':0.,'b TotalCurrent':2.,'b lHeatFlux':-1.})
    # The incoming hole at Ev=-1 contributes 1 W in addition to the
    # electron's 4 W. Separate per-species origins would incorrectly lose it.
    result=audit(values,bands)
    assert result['valid'] and result['contact_band_work_W']==5.
    assert result['contact_material_work_W']==1.
    for port in bands:
        for band in bands[port]:bands[port][band]+=1e12
    shifted=audit(values,bands,reference_energy_eV=1e12+7.)
    assert shifted['valid'] and shifted['contact_band_work_W']==5.


def test_reversing_band_work_sign_or_using_joule_values_is_rejected():
    values,bands=fixture()
    bands['b']={'conduction':2.,'valence':1.}
    assert not audit(values,bands)['valid']
    _,bands=fixture()
    bands={p:{k:v*1.602176634e-19 for k,v in b.items()} for p,b in bands.items()}
    assert not audit(values,bands)['valid']


@pytest.mark.parametrize('dimension,kwargs,scale',[
    ('1d',dict(area_um2=4.),4.),('2d',dict(depth_um=2.),2.),('3d',{},1.)])
def test_current_and_band_work_units(dimension,kwargs,scale):
    result=audit(dimension=dimension,**kwargs)
    assert result['valid'] and result['contact_band_work_W']==6*scale
    values,bands=fixture()
    for key in values:
        if key.endswith(('eCurrent','hCurrent','TotalCurrent','DisplacementCurrent')):values[key]*=scale
    result=audit(values,bands,dimension=dimension,current_unit='A',**kwargs)
    assert result['valid'] and result['contact_band_work_W']==6*scale


def test_zero_current_heat_exchange_has_no_hidden_power_floor():
    values,bands=fixture()
    for key in values:
        if 'Current' in key or key.endswith(('eHeatFlux','hHeatFlux')):values[key]=0.
    values['a lHeatFlux']=2e-15;values['b lHeatFlux']=-2e-15
    assert audit(values,bands)['valid']
    values['b lHeatFlux']-=1e-16
    assert not audit(values,bands)['valid']
    assert audit(values,bands,power_atol_W=2e-16)['valid']


def test_reported_total_current_cannot_replace_carrier_composition_check():
    values,bands=fixture();values['a eCurrent']=-2.
    result=audit(values,bands)
    assert result['power_balance_valid'] and result['terminal_current_balance_valid']
    assert not result['current_components_valid'] and not result['valid']


def test_displacement_current_is_not_accepted_as_steady_energy_transport():
    values,bands=fixture()
    values['a DisplacementCurrent']=.1;values['a hCurrent']=-.1
    values['b DisplacementCurrent']=-.1;values['b hCurrent']=.1
    result=audit(values,bands,power_atol_W=100.)
    assert result['current_components_valid'] and not result['steady_displacement_valid']
    assert not result['valid']


@pytest.mark.parametrize('port,kind',[('a','eCurrent'),('a','hCurrent'),('b','DisplacementCurrent')])
def test_missing_component_is_never_assumed_zero(port,kind):
    values,bands=fixture();del values[port+' '+kind]
    with pytest.raises(ValueError,match='missing exported dataset'):audit(values,bands)


@pytest.mark.parametrize('bands',[{}, {'a':{'conduction':0.,'valence':-1.}},
    {'a':{'conduction':0.,'valence':-1.},'b':{'conduction':-2.}},
    {'a':{'conduction':0.,'valence':-1.},'b':{'conduction':-2.,'valence':-1.}},
    {'a':{'conduction':False,'valence':-1.},'b':{'conduction':-2.,'valence':-3.}},
    {'a':{'conduction':0.,'valence':float('nan')},'b':{'conduction':-2.,'valence':-3.}}])
def test_invalid_contact_band_mapping_is_rejected(bands):
    with pytest.raises(ValueError):audit(bands=bands)


@pytest.mark.parametrize('reference',[False,float('nan'),float('inf'),'0'])
def test_invalid_energy_reference_is_rejected(reference):
    with pytest.raises(ValueError):audit(reference_energy_eV=reference)


def test_nonfinite_component_and_overflowing_band_work_are_rejected():
    values,bands=fixture();values['a eCurrent']=float('nan')
    with pytest.raises(ValueError):audit(values,bands)
    values,bands=fixture();bands['b']={'conduction':1e308,'valence':1e308}
    with pytest.raises(ValueError):audit(values,bands)


def test_audit_does_not_mutate_raw_exports_or_band_records():
    values,bands=fixture();before=deepcopy((values,bands))
    audit(values,bands)
    assert (values,bands)==before


def actual(case):
    folder=Path(__file__).resolve().parents[1]/'docs/validation/thermal_contact_work_20261018/commercial_raw'/case
    row=read_sentaurus_plt_rows(folder/'resistor_des.plt')[-1]
    bands={port:{kind:row[f'Pos({x},0.05) {dataset}'] for kind,dataset in
        [('conduction','ConductionBandEnergy'),('valence','ValenceBandEnergy')]}
        for port,x in [('left','0'),('right','0.1')]}
    return row,bands


@pytest.mark.parametrize('case',['grid640_right350_V0','grid640_left350_V0','grid640_right450_V0',
    'grid640_right350_V0.05','grid640_right350_V-0.05'])
def test_real_unequal_bath_export_uses_measured_contact_work(case):
    row,bands=actual(case)
    result=audit_sentaurus_contact_energy_flux(row,contact_band_edges_eV=bands,
        electrodes=['left','right'],thermodes=['left','right'],power_atol_W=1e-15,current_atol_A=1e-15)
    assert result['valid'] and abs(result['contact_material_work_W'])>1e-10
    assert abs(result['power_residual_W'])<=result['power_error_budget_W']
    assert not result['complete_device_energy']
    swapped=dict(left=bands['right'],right=bands['left'])
    bad=audit_sentaurus_contact_energy_flux(row,contact_band_edges_eV=swapped,
        electrodes=['left','right'],thermodes=['left','right'],power_atol_W=1e-15,current_atol_A=1e-15)
    assert not bad['valid']


@pytest.mark.parametrize('case',['grid40_right350_V0','grid160_right350_V0'])
def test_measured_contact_work_does_not_make_coarse_mesh_pass(case):
    row,bands=actual(case)
    result=audit_sentaurus_contact_energy_flux(row,contact_band_edges_eV=bands,
        electrodes=['left','right'],thermodes=['left','right'],power_atol_W=1e-15,current_atol_A=1e-15)
    assert not result['valid'] and result['current_components_valid']
