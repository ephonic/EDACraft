"""Audit the original Zenodo 10891385 cooling tables without inventing observables.

The reported temperature and its fit uncertainty describe a shared carrier
observable. Bath filename labels are metadata, and pump fluence is not density.
This module preserves original row order and clocks; it never executes author
code, aligns clocks, fills missing errors, or fits material parameters.
"""
import csv
import hashlib
import io
import math
from pathlib import PurePosixPath
import re
import zipfile

PUBLISHED_SHA256 = 'df20b29f98808148c8310eb8e51ac9d189109b077029c3ca5fa3aa13ba1f5aab'
SOURCE_URL = 'https://zenodo.org/records/10891385'
MATERIALS = ('hex-Si_0.2Ge_0.8', 'hex-Si_0.32Ge_0.68', 'QW reference sample')
COLUMNS = ('time (ns)', 'Carrier temperature (K)', 'Uncertainty Carrier temperature (K)')


def _number(text):
    if not text.strip():
        return None
    try:
        value = float(text)
    except ValueError as exc:
        raise ValueError('invalid numeric temperature-table entry') from exc
    return value if math.isfinite(value) else None


def inspect_sige_cooling_table(member, data):
    """Parse one original table; retain invalid observations with reason codes.

    ``fit_uncertainty_K`` retains the author's column without assigning a
    confidence level, covariance, or standard-uncertainty interpretation.
    """
    parts = PurePosixPath(member).parts
    if ('\\' in member or '..' in parts or len(parts) != 5 or
            parts[0] != 'Data_CarrierCooling' or parts[1] not in MATERIALS or
            parts[3] != 'fit_results'):
        raise ValueError('unrecognized original cooling-table path')
    method = re.search(r'_Carrier temperature_(LSW|Fermi-Dirac)\.csv$', parts[4])
    bath = re.search(r'_T=([0-9]+(?:\.[0-9]+)?)K_', parts[4])
    if method is None or bath is None or float(bath[1]) <= 0:
        raise ValueError('explicit method and positive bath filename label required')
    reader = csv.reader(io.StringIO(data.decode('utf-8-sig'), newline=''))
    header = next(reader, [])
    if len(header) != len(set(header)) or any(c not in header for c in COLUMNS):
        raise ValueError('unique original temperature and fit-uncertainty columns required')
    indices = [header.index(c) for c in COLUMNS]
    rows = []
    for index, raw in enumerate(reader):
        if len(raw) != len(header):
            raise ValueError('ragged temperature table')
        time_ns, temperature, uncertainty = [_number(raw[i]) for i in indices]
        reasons = []
        if time_ns is None:
            reasons.append('nonfinite_or_missing_time')
        if temperature is None or temperature <= 0:
            reasons.append('nonpositive_or_missing_temperature')
        if uncertainty is None or uncertainty <= 0:
            reasons.append('nonpositive_or_missing_fit_uncertainty')
        rows.append(dict(row_index=index, time_ns=time_ns, temperature_K=temperature,
                         fit_uncertainty_K=uncertainty, exclusion_reasons=reasons,
                         eligible_for_common_temperature_diagnostic=not reasons))
    if not rows:
        raise ValueError('nonempty temperature table required')
    times = [r['time_ns'] for r in rows]
    finite = all(t is not None for t in times)
    ordered = finite and all(b > a for a, b in zip(times, times[1:]))
    # A malformed clock invalidates a whole trace, without sorting or hiding rows.
    if not ordered:
        for row in rows:
            row['exclusion_reasons'].append('trace_clock_not_strictly_increasing')
            row['eligible_for_common_temperature_diagnostic'] = False
    eligible = sum(r['eligible_for_common_temperature_diagnostic'] for r in rows)
    return dict(member=member, sha256=hashlib.sha256(data).hexdigest(),
                material=parts[1], condition_id='/'.join(parts[:3]),
                fit_method=method[1], bath_filename_label_K=float(bath[1]),
                bath_label_is_measured_lattice_temperature=False,
                clock_origin_aligned=False, original_time_units='ns',
                strictly_increasing_clock=ordered, rows=rows, row_count=len(rows),
                eligible_row_count=eligible, excluded_row_count=len(rows)-eligible,
                uncertainty_kind='author_reported_fit_uncertainty_unspecified_coverage',
                independent_carrier_temperatures=False)


def audit_sige_cooling_archive(path, *, expected_sha256=PUBLISHED_SHA256):
    """Hash-pin the archive, deduplicate bytes, and group alternate analyses.

    Diagnostics count observed rows only. No row count establishes independence
    between time samples, fit methods, carriers, or experimental conditions.
    """
    if not isinstance(expected_sha256, str) or not re.fullmatch('[0-9a-f]{64}', expected_sha256):
        raise ValueError('explicit lowercase SHA256 required')
    sha = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            sha.update(block)
    digest = sha.hexdigest()
    if digest != expected_sha256:
        raise ValueError('cooling archive SHA256 mismatch')
    tables = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(set(names)) != len(names):
            raise ValueError('duplicate ZIP member names')
        for member in sorted(names):
            if '_Carrier temperature_' in member and member.endswith('.csv'):
                tables.append(inspect_sige_cooling_table(member, archive.read(member)))
    if not tables:
        raise ValueError('no original carrier-temperature tables')
    canonical = {}
    groups = {}
    for table in tables:
        table['duplicate_of'] = canonical.get(table['sha256'])
        canonical.setdefault(table['sha256'], table['member'])
        group = groups.setdefault(table['condition_id'], [])
        group.append(table)
    conditions = []
    for key, group in sorted(groups.items()):
        labels = sorted({t['bath_filename_label_K'] for t in group})
        if len(labels) != 1:
            raise ValueError('inconsistent bath labels within experimental condition')
        clocks_differ = any([r['time_ns'] for r in t['rows']] !=
                            [r['time_ns'] for r in group[0]['rows']] for t in group[1:])
        conditions.append(dict(condition_id=key, material=group[0]['material'],
                               members=[t['member'] for t in group],
                               bath_filename_label_K=labels[0],
                               unique_table_contents=len({t['sha256'] for t in group}),
                               alternate_analysis_clocks_differ=clocks_differ,
                               may_split_analyses_between_training_and_holdout=False))
    material_design = []
    for material in sorted({t['material'] for t in tables}):
        labels = sorted({t['bath_filename_label_K'] for t in tables if t['material'] == material})
        material_design.append(dict(material=material, bath_filename_labels_K=labels,
            measured_lattice_temperature_conditions=0, measured_density_conditions=0,
            ac_design_rank=None, ac_joint_identifiable=False,
            constant_bath_label_confounds_a_with_tau0=len(labels) == 1))
    return dict(source_url=SOURCE_URL, archive_sha256=digest,
        matches_published_archive=digest == PUBLISHED_SHA256,
        table_count=len(tables), unique_table_contents=len(canonical),
        condition_count=len(conditions), row_count=sum(t['row_count'] for t in tables),
        unique_content_row_count=sum(t['row_count'] for t in tables if t['duplicate_of'] is None),
        tables=tables, conditions=conditions, material_design=material_design,
        missing_required_observations=['independent_electron_temperature_with_uncertainty',
            'independent_hole_temperature_with_uncertainty',
            'measured_lattice_temperature_with_uncertainty',
            'carrier_density_and_uncertainty', 'same_material_lattice_temperature_excitation',
            'verified_postpulse_energy_and_particle_balance'],
        fluence_used_as_density=False, fitted_parameters={}, author_code_executed=False,
        real_material_ac_joint_calibration=False,
        ready_for_independent_three_temperature_acceptance=False,
        experimental_validated=False, physical_validated=False, complete_device_energy=False)


def assert_disjoint_cooling_conditions(report, calibration_members, holdout_members):
    """Reject condition leakage, including identical files and alternate fits.

    This partition check does not qualify cooling data as a material calibration.
    A material fit must supply the missing physics and measured observables.
    """
    by_member = {t['member']: t for t in report['tables']}
    groups = []
    for supplied in (calibration_members, holdout_members):
        supplied = tuple(supplied)
        if not supplied or len(set(supplied)) != len(supplied) or any(n not in by_member for n in supplied):
            raise ValueError('nonempty unique known members required in each partition')
        groups.append([by_member[n] for n in supplied])
    if len({t['material'] for group in groups for t in group}) != 1:
        raise ValueError('one material identity required for calibration and holdout')
    for key in ('condition_id', 'sha256'):
        if {t[key] for t in groups[0]} & {t[key] for t in groups[1]}:
            raise ValueError('experimental condition or source leakage across partitions')
    return True
