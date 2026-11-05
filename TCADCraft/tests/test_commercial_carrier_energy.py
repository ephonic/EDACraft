"""SI/sign conventions, missing carrier exports, KCL and real DF-ISE data."""
from pathlib import Path
import pytest

from tcad.postprocess.commercial_energy import read_sentaurus_plt_rows, audit_sentaurus_hydrodynamic_flux


def row():
    return {'a OuterVoltage':0.,'b OuterVoltage':2.,
            'a TotalCurrent':-3.,'b TotalCurrent':3.,
            'a lHeatFlux':-2.,'b lHeatFlux':-2.,
            'a eHeatFlux':1.,'b eHeatFlux':-2.5,
            'a hHeatFlux':.25,'b hHeatFlux':-.75}


def audit(values=None,**kwargs):
    options=dict(electrodes=['a','b'],thermodes=['a','b'],power_atol_W=0.,current_atol_A=0.,
                 power_rtol=0.,current_rtol=0.)
    options.update(kwargs)
    return audit_sentaurus_hydrodynamic_flux(row() if values is None else values,**options)


@pytest.mark.parametrize('dimension,extrusion,scale',[
    ('1d',{'area_um2':4.},4.),('2d',{'depth_um':2.},2.),('3d',{},1.)])
def test_signed_three_component_balance_and_dimensional_current_conversion(dimension,extrusion,scale):
    result=audit(dimension=dimension,**extrusion)
    assert result['valid']
    assert result['electrical_power_W']==result['outward_heat_power_W']==6*scale
    assert result['outward_electron_heat_power_W']==1.5*scale
    assert result['outward_hole_heat_power_W']==.5*scale
    assert result['outward_lattice_heat_power_W']==4*scale
    assert result['thermode_outward_heat_W']['eHeatFlux']['a']==-scale
    assert result['carrier_energy_flux_exported']
    assert not result['complete_device_energy'] and not result['physical_validated']


def test_already_integrated_current_is_not_scaled_twice():
    values=row();values['a TotalCurrent']*=2;values['b TotalCurrent']*=2
    assert audit(values,depth_um=2.,current_unit='A')['valid']
    assert not audit(values,depth_um=2.)['valid']


def test_lattice_only_false_closure_is_detected_and_missing_carriers_rejected():
    values=row();values['a lHeatFlux']=-3.;values['b lHeatFlux']=-3.
    assert not audit(values)['valid']
    for port in ('a','b'):
        for component in ('eHeatFlux','hHeatFlux','lHeatFlux'):
            bad=row();del bad[port+' '+component]
            with pytest.raises(ValueError,match='missing exported dataset'): audit(bad)


def test_current_balance_failure_is_mandatory_even_if_power_balances():
    values=row();values['a TotalCurrent']=0.
    result=audit(values)
    assert result['power_balance_valid']
    assert not result['terminal_current_balance_valid'] and not result['valid']


def test_common_voltage_shift_does_not_hide_kcl_or_change_power():
    values=row()
    for port in ('a','b'): values[port+' OuterVoltage']+=1e12
    assert audit(values)['electrical_power_W']==6.
    assert audit(values,reference_voltage_V=1e12-100.)['electrical_power_W']==6.
    values['a TotalCurrent']+=.001
    assert not audit(values,power_atol_W=1e6)['valid']


def test_heat_exchange_at_zero_electrical_power_uses_absolute_watt_budget():
    values=row()
    for port in ('a','b'):
        values[port+' TotalCurrent']=0.
        values[port+' eHeatFlux']=0.; values[port+' hHeatFlux']=0.
    values['a lHeatFlux']=2e-10;values['b lHeatFlux']=-2e-10
    assert audit(values)['valid']
    values['b lHeatFlux']-=1e-15
    assert not audit(values)['valid']
    assert audit(values,power_atol_W=2e-15)['valid']


@pytest.mark.parametrize('change',[
    {'electrodes':['a','a']},{'thermodes':'ab'},{'electrodes':[]},
    {'thermodes':[False]},{'dimension':'2D'},{'current_unit':'A/um'},
    {'depth_um':0.},{'area_um2':-1.,'dimension':'1d'},
    {'power_atol_W':True},{'current_atol_A':float('nan')},
    {'power_rtol':-1.},{'current_rtol':float('inf')},{'reference_voltage_V':False}])
def test_invalid_contract_is_rejected(change):
    with pytest.raises(ValueError): audit(**change)


@pytest.mark.parametrize('dataset',['a TotalCurrent','b OuterVoltage','a eHeatFlux','b hHeatFlux'])
@pytest.mark.parametrize('value',[True,float('inf'),float('nan'),'1.'])
def test_nonfinite_or_nonnumeric_exports_rejected(dataset,value):
    values=row();values[dataset]=value
    with pytest.raises(ValueError): audit(values)


def test_finite_inputs_that_overflow_power_are_rejected():
    values=row();values['b TotalCurrent']=1e308;values['b OuterVoltage']=1e308
    with pytest.raises(ValueError): audit(values)


def write_plt(path,names,data):
    path.write_text('DF-ISE text\nInfo { datasets = [ '+names+' ] }\nData { '+data+' }\n')


def test_complete_plt_rows_preserve_names_and_fortran_exponents(tmp_path):
    path=tmp_path/'data.plt'
    write_plt(path,'"a eHeatFlux" "b eHeatFlux"','1D-20 -2d-20\n3e-20 -4e-20')
    assert read_sentaurus_plt_rows(path)==[
        {'a eHeatFlux':1e-20,'b eHeatFlux':-2e-20},
        {'a eHeatFlux':3e-20,'b eHeatFlux':-4e-20}]


@pytest.mark.parametrize('names,data',[('"a" "a"','1 2'),('"a" "b"','1 2 3'),
    ('"a"','nan'),('"a"','inf'),('"a"',''),('a','1'),('"a" junk','1'),('"a"','1 garbage')])
def test_malformed_complete_plt_is_rejected(tmp_path,names,data):
    path=tmp_path/'bad.plt';write_plt(path,names,data)
    with pytest.raises(ValueError): read_sentaurus_plt_rows(path)


def test_partial_plt_cannot_be_mistaken_for_an_accepted_solve(tmp_path):
    path=tmp_path/'partial.plt'
    path.write_text('DF-ISE text\nInfo { datasets = [ "a" ] }\nData { 1\n')
    with pytest.raises(ValueError): read_sentaurus_plt_rows(path)


def test_duplicate_data_blocks_are_ambiguous(tmp_path):
    path=tmp_path/'ambiguous.plt'
    path.write_text('DF-ISE text\nInfo { datasets = [ "a" ] }\nData { 1 }\nData { 2 }\n')
    with pytest.raises(ValueError): read_sentaurus_plt_rows(path)


def test_fresh_coarse_hydrodynamic_export_has_carriers_and_is_honestly_rejected():
    directory=Path(__file__).resolve().parents[1]/'docs/validation/carrier_heat_flux_20261018'
    rows=read_sentaurus_plt_rows(directory/'commercial_raw/grid40_L300_R300_V0.3/resistor_des.plt')
    result=audit_sentaurus_hydrodynamic_flux(rows[-1],electrodes=['left','right'],thermodes=['left','right'],
        power_atol_W=1e-15,current_atol_A=1e-15,power_rtol=.001)
    assert result['carrier_energy_flux_exported'] and not result['valid']
    assert result['outward_electron_heat_power_W']>2e-7
    assert rows[-1]['MaxSilicon eTemperature']>500.


@pytest.mark.parametrize('case',['grid640_L300_R300_V0.3','grid640_L450_R450_V0.3','grid640_L300_R300_V-0.3'])
def test_fresh_refined_export_passes_independent_three_component_gate(case):
    directory=Path(__file__).resolve().parents[1]/'docs/validation/carrier_heat_flux_20261018'
    rows=read_sentaurus_plt_rows(directory/'commercial_raw'/case/'resistor_des.plt')
    result=audit_sentaurus_hydrodynamic_flux(rows[-1],electrodes=['left','right'],thermodes=['left','right'],
        power_atol_W=1e-15,current_atol_A=1e-15,power_rtol=.001)
    assert result['valid'] and result['carrier_energy_flux_exported']
    # Dropping the explicitly exported electronic heat must fail this gate.
    bad=rows[-1].copy();bad['left eHeatFlux']=0.;bad['right eHeatFlux']=0.
    assert not audit_sentaurus_hydrodynamic_flux(bad,electrodes=['left','right'],thermodes=['left','right'],
        power_atol_W=1e-15,current_atol_A=1e-15,power_rtol=.001)['valid']
