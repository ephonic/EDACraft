"""Read the original Lu 2026 workbook without inventing missing observables.

The source's Te profile and peak/force table have different sampling axes.
Calculated pressures at prescribed temperatures are not measured temperatures.
Author error bars retain their unspecified coverage; no standard uncertainty,
lattice temperature, hole temperature or new condition is inferred from them.
"""
import hashlib
import io
import math
from decimal import Decimal,InvalidOperation
from pathlib import PurePosixPath
import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile

PUBLISHED_SHA256='47b7d02db86dd9bcb30e0e4bda23fe317a089d812f97d55d56ef81b458ca2e45'
SOURCE_URL='https://www.nature.com/articles/s41467-026-71712-5'
_NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def _source_sheets(data):
    """Decode stored OOXML values only; never evaluate formulas or external links."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names=archive.namelist()
        if len(set(names))!=len(names):raise ValueError('duplicate workbook ZIP members')
        if archive.testzip() is not None:raise ValueError('workbook CRC mismatch')
        if any('/externalLinks/' in '/'+n for n in names):raise ValueError('external workbook links are not source observations')
        strings=[]
        if 'xl/sharedStrings.xml' in names:
            strings=[''.join(t.text or '' for t in n.findall('.//s:t',_NS))
                     for n in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si',_NS)]
        relations={}
        for rel in ET.fromstring(archive.read('xl/_rels/workbook.xml.rels')):
            if rel.get('TargetMode')=='External':raise ValueError('external workbook relationship')
            target=rel.attrib['Target']
            member=posixpath.normpath(target.lstrip('/') if target.startswith('/xl/') else 'xl/'+target)
            if '\\' in target or not member.startswith('xl/') or '..' in PurePosixPath(member).parts:
                raise ValueError('workbook relationship outside xl')
            relations[rel.attrib['Id']]=member
        sheets={}
        for sheet in ET.fromstring(archive.read('xl/workbook.xml')).findall('s:sheets/s:sheet',_NS):
            name=sheet.attrib['name']
            if name in sheets:raise ValueError('duplicate source sheet name')
            rid=sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
            cells={}
            for c in ET.fromstring(archive.read(relations[rid])).findall('.//s:sheetData/s:row/s:c',_NS):
                address=c.attrib['r'];kind=c.get('t','n');v=c.find('s:v',_NS);formula=c.find('s:f',_NS)
                value=v.text if v is not None else None
                if kind=='s':value=strings[int(value)]
                if kind=='inlineStr':value=''.join(t.text or '' for t in c.findall('.//s:t',_NS))
                if value is None and formula is None:continue
                if address in cells:raise ValueError('duplicate source cell address')
                cells[address]=dict(type=kind,value=value,formula=formula.text if formula is not None else None)
            sheets[name]=cells
    return sheets


def _number(cell):
    if cell is None or cell.get('type')!='n' or cell.get('formula') is not None:return None
    try:
        value=float(cell['value'])
        if value==0 and Decimal(cell['value'])!=0:return None
    except (TypeError,ValueError,OverflowError,InvalidOperation):return None
    return value if math.isfinite(value) else None


def _inspect_tables(sheets):
    if set(sheets)!={'Fig.2c','Fig.2f','Fig.3','Fig.4'}:raise ValueError('unrecognized original source sheets')
    cells=sheets['Fig.4']
    expected={'A2':'x(um)','B2':'Te(K)','F2':'Te(K)','G2':'Te error(K)',
              'H2':'Force gradient(N/m)','I2':'Force gradient error(N/m)'}
    for address,label in expected.items():
        c=cells.get(address,{})
        if c.get('value')!=label or c.get('formula') is not None:raise ValueError('original Fig.4 headers changed: '+address)
    def rows_for(columns):
        return sorted({int(m[2]) for address in cells
                       if (m:=re.fullmatch(r'([A-Z]+)([1-9][0-9]*)',address))
                       and m[1] in columns and int(m[2])>=3})
    spatial=[]
    for row in rows_for(('A','B')):
        x=_number(cells.get('A'+str(row)));te=_number(cells.get('B'+str(row)))
        reasons=[]
        if x is None or not math.isfinite(x*1e-6):reasons.append('coordinate_missing_or_nonfinite')
        elif x!=0 and x*1e-6==0:reasons.append('coordinate_not_representable_in_metres')
        if te is None or te<=0:reasons.append('temperature_missing_or_nonpositive')
        spatial.append(dict(source_row=row,source_cells=['A'+str(row),'B'+str(row)],
            original_values={k:cells.get(k+str(row)) for k in ('A','B')},x_um=x,
            x_m=x*1e-6 if x is not None and math.isfinite(x*1e-6) and (x==0 or x*1e-6!=0) else None,
            reported_Te_K=te,measurement_uncertainty_K=None,numeric_row_valid=not reasons,reasons=reasons))
    peak=[]
    for row in rows_for(('F','G','H','I')):
        values={key:_number(cells.get(col+str(row))) for col,key in
                (('F','reported_Te_K'),('G','reported_Te_error_K'),('H','force_gradient_N_m'),('I','force_gradient_error_N_m'))}
        reasons=[]
        if any(v is None for v in values.values()):reasons.append('missing_or_nonfinite_observation')
        if any(values[k] is not None and values[k]<=0 for k in ('reported_Te_K','reported_Te_error_K','force_gradient_error_N_m')):
            reasons.append('nonpositive_temperature_or_reported_error')
        peak.append(dict(source_row=row,original_values={k:cells.get(k+str(row)) for k in ('F','G','H','I')},
                         **values,numeric_row_valid=not reasons,reasons=reasons))
    if not spatial or not peak:raise ValueError('both original electron observation tables required')
    xs=[r['x_m'] for r in spatial]
    ordered=all(v is not None for v in xs) and all(b>a for a,b in zip(xs,xs[1:]))
    return dict(sheet_inventory=[dict(name=name,nonempty_cells=len(table),
                formula_count=sum(c.get('formula') is not None for c in table.values()),
                headers={a:c['value'] for a,c in table.items() if re.fullmatch('[A-Z]+[12]',a)})
                for name,table in sheets.items()],
        spatial_electron_table=dict(sheet='Fig.4',coordinate_header='x(um)',temperature_header='Te(K)',
            row_count=len(spatial),rows=spatial,strictly_increasing_coordinates=ordered,
            original_order_preserved=True,uncertainty_rows_available=0,
            eligible_for_pointwise_uncertainty_acceptance=False),
        peak_electron_force_table=dict(sheet='Fig.4',row_count=len(peak),rows=peak,
            uncertainty_kind='author_reported_Te_error_unspecified_coverage',
            standard_uncertainty_K=None,physical_condition_coordinates_supplied=False,
            error_bars_may_be_transferred_to_spatial_rows=False),
        measured_temperature_coverage=dict(electron_temperature=any(r['numeric_row_valid'] for r in spatial+peak),
                                          hole_temperature=False,lattice_temperature=False),
        calculated_pressure_columns_are_temperature_measurements=False,
        fitted_line_columns_are_measured_observations=False,
        observation_axes_aligned=False,lattice_temperature_inferred_from_error_bars=False,
        temperature_offset_applied_K=0.,data_sorted=False,missing_errors_imputed=False,
        missing_required_observations=['independent_hole_temperature_and_uncertainty',
            'numeric_measured_lattice_temperature_and_uncertainty',
            'pointwise_spatial_electron_temperature_uncertainty',
            'temperature_error_coverage_definition','independent_material_density_and_lattice_excitation',
            'whole_condition_calibration_holdout_partition','transient_temperature_clocks'],
        measured_ac_design_rank=None,fitted_parameters={},
        ready_for_independent_three_temperature_acceptance=False,real_material_ac_joint_calibration=False,
        solver_prediction_compared=False,experimental_validated=False,physical_validated=False,complete_device_energy=False)


def audit_lu_thermal_force_workbook(path,*,expected_sha256=PUBLISHED_SHA256):
    """Hash-pin the supplied workbook and retain original table values/axes.

    A nondefault expected hash permits explicitly identified software controls;
    the report separately states whether bytes match the published workbook.
    No metadata authenticates a new experimental condition or its uncertainty.
    """
    if not isinstance(expected_sha256,str) or not re.fullmatch('[0-9a-f]{64}',expected_sha256):
        raise ValueError('explicit lowercase SHA256 required')
    with open(path,'rb') as stream:data=stream.read()
    digest=hashlib.sha256(data).hexdigest()
    if digest!=expected_sha256:raise ValueError('thermal-force workbook SHA256 mismatch')
    return dict(source_url=SOURCE_URL,workbook_sha256=digest,matches_published_workbook=digest==PUBLISHED_SHA256,
                author_code_executed=False,workbook_modified=False,**_inspect_tables(_source_sheets(data)))
