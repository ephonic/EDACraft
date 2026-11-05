"""Admission of actual source rows, with explicit tests of common leakage modes."""
import hashlib
import json
from pathlib import Path
import zipfile
import pytest
from tcad.validation.sige_cooling import (
    PUBLISHED_SHA256, inspect_sige_cooling_table, audit_sige_cooling_archive,
    assert_disjoint_cooling_conditions,
)

MEMBER = ('Data_CarrierCooling/hex-Si_0.2Ge_0.8/hex-Si0.2Ge0.8_3.45mJcm^2/'
          'fit_results/H07772_T=7K_example_Carrier temperature_LSW.csv')
HEADER = 'time (ns),Carrier temperature (K),Uncertainty Carrier temperature (K)\n'
RAW = Path(__file__).resolve().parents[1] / (
    'docs/validation/energy_coordinate_reservoirs_20261022/research_evidence/zenodo10891385')


@pytest.fixture(scope='module')
def original():
    return audit_sige_cooling_archive(RAW/'Data_CarrierCooling.zip')


def test_original_archive_matches_every_previous_inventory_hash_and_row_count(original):
    inventory = json.loads((RAW/'temperature_inventory.json').read_text())
    old = {t['member']: t for t in inventory['tables']}
    assert original['archive_sha256'] == PUBLISHED_SHA256
    assert original['matches_published_archive']
    assert original['table_count'] == 11 and original['row_count'] == 6423
    assert set(old) == {t['member'] for t in original['tables']}
    for table in original['tables']:
        assert table['sha256'] == old[table['member']]['sha256']
        assert table['row_count'] == old[table['member']]['rows']
        assert [r['row_index'] for r in table['rows']] == list(range(table['row_count']))
    json.dumps(original, allow_nan=False)


def test_actual_duplicate_and_alternate_fit_are_not_independent_conditions(original):
    duplicates = [t for t in original['tables'] if t['duplicate_of']]
    assert len(duplicates) == 1 and duplicates[0]['row_count'] == 665
    assert original['unique_table_contents'] == 10
    assert original['unique_content_row_count'] == 5758
    assert original['condition_count'] == 9
    alternate = [c for c in original['conditions'] if c['alternate_analysis_clocks_differ']]
    assert len(alternate) == 1 and '3.45mJcm^2' in alternate[0]['condition_id']
    assert alternate[0]['unique_table_contents'] == 2
    # Keep the uncorrected repository fluence label and original clocks.
    group = [t for t in original['tables'] if t['condition_id'] == alternate[0]['condition_id']]
    assert {t['fit_method']: t['rows'][0]['time_ns'] for t in group} == {
        'LSW': 0., 'Fermi-Dirac': 1.248}
    assert not any(t['clock_origin_aligned'] for t in original['tables'])


def test_original_qw_uncertainties_are_missing_and_negative_times_are_retained(original):
    qw = [t for t in original['tables'] if t['material'] == 'QW reference sample']
    assert sum(t['row_count'] for t in qw) == 1875
    assert sum(t['eligible_row_count'] for t in qw) == 0
    assert all(r['fit_uncertainty_K'] is None for t in qw for r in t['rows'])
    assert any(r['time_ns'] < 0 for t in original['tables'] for r in t['rows'])
    assert all(t['strictly_increasing_clock'] for t in original['tables'])


def test_real_rows_keep_values_errors_and_no_invented_density_or_lattice(original):
    table = next(t for t in original['tables'] if '3.45mJ' in t['member'] and t['fit_method'] == 'LSW')
    assert table['rows'][0]['temperature_K'] == pytest.approx(774.54726049)
    assert table['rows'][0]['fit_uncertainty_K'] == pytest.approx(41.52542946)
    assert table['uncertainty_kind'].endswith('unspecified_coverage')
    assert not table['bath_label_is_measured_lattice_temperature']
    assert not original['fluence_used_as_density'] and not original['fitted_parameters']
    for design in original['material_design']:
        assert design['ac_design_rank'] is None
        assert not design['ac_joint_identifiable']
        assert design['measured_lattice_temperature_conditions'] == design['measured_density_conditions'] == 0
    assert not original['real_material_ac_joint_calibration']
    assert not original['ready_for_independent_three_temperature_acceptance']
    assert not original['experimental_validated'] and not original['author_code_executed']


@pytest.mark.parametrize('kind', ['exact_duplicate', 'alternate_analysis'])
def test_actual_training_holdout_leakage_rejected(original, kind):
    condition = next(c for c in original['conditions'] if
        (c['unique_table_contents'] == 2 if kind == 'alternate_analysis' else len(c['members']) > c['unique_table_contents']))
    with pytest.raises(ValueError, match='leakage'):
        assert_disjoint_cooling_conditions(original, condition['members'][:1], condition['members'][1:])


def test_materials_cannot_supply_each_others_lattice_excitation(original):
    a = next(t for t in original['tables'] if t['material'] == 'hex-Si_0.2Ge_0.8')
    b = next(t for t in original['tables'] if t['material'] == 'hex-Si_0.32Ge_0.68')
    with pytest.raises(ValueError, match='material identity'):
        assert_disjoint_cooling_conditions(original, [a['member']], [b['member']])
    assert len({c['bath_filename_label_K'] for c in original['conditions'] if c['material'] == a['material']}) == 1


def test_whole_separate_same_material_conditions_can_be_partitioned(original):
    group = [c for c in original['conditions'] if c['material'] == 'hex-Si_0.32Ge_0.68']
    assert assert_disjoint_cooling_conditions(original, group[0]['members'], group[1]['members'])


@pytest.mark.parametrize('bad', [[], ['unknown'], [MEMBER, MEMBER]])
def test_empty_unknown_or_repeated_partition_rejected(original, bad):
    with pytest.raises(ValueError, match='unique known'):
        assert_disjoint_cooling_conditions(original, bad, [original['tables'][0]['member']])


@pytest.mark.parametrize('entry,reason', [('nan','missing'), ('inf','missing'), ('','missing'), ('0','nonpositive'), ('-2','nonpositive')])
def test_missing_and_invalid_uncertainties_retained_without_fabrication(entry, reason):
    table = inspect_sige_cooling_table(MEMBER, (HEADER+f'0,400,{entry}\n1,350,2\n').encode())
    assert table['row_count'] == 2 and table['eligible_row_count'] == 1
    assert reason in table['rows'][0]['exclusion_reasons'][0]
    assert table['rows'][1]['fit_uncertainty_K'] == 2
    json.dumps(table, allow_nan=False)


@pytest.mark.parametrize('times', [('0','0'), ('1','0'), ('nan','1')])
def test_bad_trace_clock_invalidates_trace_without_sorting(times):
    table = inspect_sige_cooling_table(MEMBER, (HEADER+f'{times[0]},400,1\n{times[1]},350,1\n').encode())
    assert not table['strictly_increasing_clock'] and table['eligible_row_count'] == 0
    assert table['row_count'] == 2
    assert all('trace_clock_not_strictly_increasing' in r['exclusion_reasons'] for r in table['rows'])


@pytest.mark.parametrize('text', [HEADER, HEADER+'0,400\n', HEADER+'0,wrong,1\n',
    'time (ns),Carrier temperature (K)\n0,400\n', HEADER.rstrip()+',time (ns)\n0,400,1,0\n'])
def test_ambiguous_or_malformed_tables_rejected(text):
    with pytest.raises(ValueError):
        inspect_sige_cooling_table(MEMBER, text.encode())


@pytest.mark.parametrize('member', [MEMBER.replace('hex-Si_0.2Ge_0.8','Other'),
    MEMBER.replace('T=7K','T=0K'), MEMBER.replace('_LSW.csv','_unknown.csv'),
    '../'+MEMBER, MEMBER.replace('/', '\\')])
def test_unknown_or_unsafe_member_not_reinterpreted(member):
    with pytest.raises(ValueError):
        inspect_sige_cooling_table(member, (HEADER+'0,400,1\n').encode())


def test_archive_hash_gate_and_nonpublished_fixture_provenance(tmp_path):
    path = tmp_path/'example.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr(MEMBER, HEADER+'0,400,1\n1,350,1\n')
    with pytest.raises(ValueError, match='SHA256 mismatch'):
        audit_sige_cooling_archive(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    report = audit_sige_cooling_archive(path, expected_sha256=digest)
    assert not report['matches_published_archive']
    assert not report['real_material_ac_joint_calibration']


def test_ambiguous_zip_member_names_rejected(tmp_path):
    path = tmp_path/'duplicate.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr(MEMBER, HEADER+'0,400,1\n')
        with pytest.warns(UserWarning):
            archive.writestr(MEMBER, HEADER+'0,450,1\n')
    with pytest.raises(ValueError, match='duplicate ZIP'):
        audit_sige_cooling_archive(path, expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
