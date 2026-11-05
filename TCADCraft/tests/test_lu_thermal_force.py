"""Original measured electron observations retain their missing axes/errors."""
from copy import deepcopy
from pathlib import Path
import hashlib
import pytest
from tcad.validation.lu_thermal_force import (PUBLISHED_SHA256,audit_lu_thermal_force_workbook,
                                            _source_sheets,_inspect_tables)

SOURCE=Path(__file__).resolve().parents[1]/'docs/validation/lu_thermal_force_20261022/experimental_raw/41467_2026_71712_MOESM3_ESM.xlsx'


@pytest.fixture
def tables():
    return _source_sheets(SOURCE.read_bytes())


def test_original_source_bytes_and_exact_observation_counts():
    before=SOURCE.read_bytes();r=audit_lu_thermal_force_workbook(SOURCE)
    assert r['workbook_sha256']==PUBLISHED_SHA256 and r['matches_published_workbook']
    assert [s['nonempty_cells'] for s in r['sheet_inventory']]==[1088,1331,2068,1490]
    assert r['spatial_electron_table']['row_count']==97 and r['peak_electron_force_table']['row_count']==5
    assert all(s['formula_count']==0 for s in r['sheet_inventory'])
    assert SOURCE.read_bytes()==before and not r['workbook_modified'] and not r['author_code_executed']


def test_original_values_row_addresses_units_and_order_are_retained():
    r=audit_lu_thermal_force_workbook(SOURCE);p=r['spatial_electron_table']
    assert p['strictly_increasing_coordinates'] and p['original_order_preserved']
    first=p['rows'][0]
    assert first['source_row']==3 and first['source_cells']==['A3','B3']
    assert first['original_values']['A']['value']=='0.48'
    assert first['reported_Te_K']==414.41213 and first['x_m']==pytest.approx(.48e-6)
    assert max(v['reported_Te_K'] for v in p['rows'])==930.58187
    assert all(v['numeric_row_valid'] for v in p['rows'])
    assert r['temperature_offset_applied_K']==0 and not r['data_sorted']


def test_peak_errors_are_not_transferred_to_spatial_points_or_declared_standard():
    r=audit_lu_thermal_force_workbook(SOURCE);s=r['spatial_electron_table'];p=r['peak_electron_force_table']
    assert all(row['measurement_uncertainty_K'] is None for row in s['rows'])
    assert not s['eligible_for_pointwise_uncertainty_acceptance'] and s['uncertainty_rows_available']==0
    assert p['rows'][0]['reported_Te_error_K']==42.75625 and p['rows'][-1]['reported_Te_K']==1155.125
    assert p['standard_uncertainty_K'] is None and not p['error_bars_may_be_transferred_to_spatial_rows']
    assert not p['physical_condition_coordinates_supplied'] and not r['observation_axes_aligned']
    assert not r['missing_errors_imputed']


def test_prescribed_lattice_pressure_and_fitted_lines_cannot_supply_missing_observations():
    r=audit_lu_thermal_force_workbook(SOURCE)
    assert r['measured_temperature_coverage']==dict(electron_temperature=True,hole_temperature=False,lattice_temperature=False)
    assert not r['calculated_pressure_columns_are_temperature_measurements']
    assert not r['fitted_line_columns_are_measured_observations']
    assert not r['lattice_temperature_inferred_from_error_bars']
    assert r['measured_ac_design_rank'] is None and r['fitted_parameters']=={}
    for key in ('ready_for_independent_three_temperature_acceptance','real_material_ac_joint_calibration',
                'solver_prediction_compared','experimental_validated','physical_validated','complete_device_energy'):
        assert r[key] is False


@pytest.mark.parametrize('digest',['0'*64,PUBLISHED_SHA256.upper(),'',None,True,'g'*64])
def test_wrong_or_undefined_source_hash_rejected(digest):
    with pytest.raises(ValueError):audit_lu_thermal_force_workbook(SOURCE,expected_sha256=digest)


def test_explicitly_pinned_unrecognized_source_is_not_silently_read(tmp_path):
    p=tmp_path/'invalid.bin';p.write_bytes(b'not a workbook')
    from zipfile import BadZipFile
    with pytest.raises(BadZipFile):audit_lu_thermal_force_workbook(p,expected_sha256=hashlib.sha256(p.read_bytes()).hexdigest())


@pytest.mark.parametrize('address',['A2','B2','F2','G2','H2','I2'])
def test_changed_units_or_meanings_are_rejected(tables,address):
    tables['Fig.4'][address]['value']='different observable or units'
    with pytest.raises(ValueError,match='headers changed'):_inspect_tables(tables)


@pytest.mark.parametrize('value',['NaN','Infinity','-Infinity','1e400','1e-400','not numeric'])
def test_nonrepresentable_original_numeric_rows_are_exposed_without_deletion(tables,value):
    tables['Fig.4']['B3']['value']=value
    result=_inspect_tables(tables)['spatial_electron_table']
    assert result['row_count']==97 and not result['rows'][0]['numeric_row_valid']
    assert result['rows'][0]['reported_Te_K'] is None and result['rows'][0]['original_values']['B']['value']==value


@pytest.mark.parametrize('kind',['missing','formula','text','zero','negative'])
def test_missing_or_invalid_peak_error_is_retained_as_invalid_not_zero_filled(tables,kind):
    if kind=='missing':del tables['Fig.4']['G3']
    if kind=='formula':tables['Fig.4']['G3']['formula']='0.2*(F3-300)'
    if kind=='text':tables['Fig.4']['G3']['type']='s'
    if kind=='zero':tables['Fig.4']['G3']['value']='0'
    if kind=='negative':tables['Fig.4']['G3']['value']='-1'
    result=_inspect_tables(tables)['peak_electron_force_table']
    assert result['row_count']==5 and not result['rows'][0]['numeric_row_valid']
    assert result['standard_uncertainty_K'] is None


def test_disordered_spatial_points_are_not_sorted(tables):
    tables['Fig.4']['A3']['value']='10'
    result=_inspect_tables(tables)['spatial_electron_table']
    assert not result['strictly_increasing_coordinates'] and result['rows'][0]['x_um']==10
    assert result['row_count']==97 and result['original_order_preserved']


def test_missing_temperature_cell_preserves_original_coordinate_and_source_row(tables):
    del tables['Fig.4']['B3']
    result=_inspect_tables(tables)['spatial_electron_table']
    assert result['row_count']==97 and result['rows'][0]['source_row']==3
    assert result['rows'][0]['x_m']==pytest.approx(.48e-6)
    assert result['rows'][0]['reported_Te_K'] is None and not result['rows'][0]['numeric_row_valid']


def test_unrecognized_sheet_coverage_is_rejected(tables):
    del tables['Fig.2f']
    with pytest.raises(ValueError,match='source sheets'):_inspect_tables(tables)


def test_decoding_tables_is_read_only(tables):
    before=deepcopy(tables);_inspect_tables(tables)
    assert tables==before
