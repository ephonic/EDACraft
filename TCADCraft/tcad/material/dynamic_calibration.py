"""Traceable pulse-duration calibration with entire drive curves held out.

The measured observable is the workbook's normalized switched polarization,
not absolute P(t), leakage current or an identified Landau viscosity. The
nominal field is voltage/film thickness; interfacial voltage division is not
measured. Never extrapolate these coefficients to another film/temperature.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
from scipy.optimize import least_squares

SOURCE_SHA256='e72057857b0185867693a55a8ebc108e36982385ffdb8ac1e68ca95c5f35b6af'
SOURCE_URL='https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41467-024-47194-8/MediaObjects/41467_2024_47194_MOESM4_ESM.xlsx'
ARTICLE='https://www.nature.com/articles/s41467-024-47194-8'
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


@dataclass(frozen=True)
class SwitchingCurve:
    times_s: tuple
    normalized_switched_polarization: tuple
    voltage_V: float
    nominal_field_V_m: float
    specimen: str
    source_sha256: str
    source_sheet: str
    source_cells: tuple
    unavailable_source_cells: tuple = ()


def load_published_hafnia_curves(path, *, specimen):
    """Read original Fig.4 a/b measured points only, preserving cell provenance.

    SI times and nominal V/6nm fields. No clipping, sorting, monotonicization,
    interpolation or re-normalization of measured switched-polarization data.
    Reject unknown bytes/labels instead of guessing a workbook schema.
    """
    sheets={'LT:HfO2':'Fig.4 a','La:HfO2':'Fig.4 b'}
    if specimen not in sheets: raise ValueError('choose the exact LT:HfO2 or La:HfO2 specimen')
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256: raise ValueError('source workbook SHA256 mismatch')
    with zipfile.ZipFile(path) as book:
        strings=[''.join(x.itertext()) for x in ET.fromstring(book.read('xl/sharedStrings.xml'))]
        workbook=ET.fromstring(book.read('xl/workbook.xml'))
        sheet=next(s for s in workbook.find('s:sheets',NS) if s.attrib['name']==sheets[specimen])
        rid=sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
        relations=ET.fromstring(book.read('xl/_rels/workbook.xml.rels'))
        target=next(x.attrib['Target'] for x in relations if x.attrib['Id']==rid)
        target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
        tree=ET.fromstring(book.read(target));cells={}
        for cell in tree.findall('.//s:c',NS):
            value=cell.find('s:v',NS)
            if value is not None: cells[cell.attrib['r']]=strings[int(value.text)] if cell.attrib.get('t')=='s' else float(value.text)
    curves=[]
    for tcol,pcol,voltage in zip('ACEGIK','BDFHJL',(4.2,4.,3.8,3.5,3.,2.5)):
        if cells.get(pcol+'2','').strip()!=f'{voltage:g}V': raise ValueError('source voltage label changed')
        times=[];values=[];refs=[];missing=[]
        for row in range(3, max(int(''.join(filter(str.isdigit,c))) for c in cells)+1):
            tc,pc=f'{tcol}{row}',f'{pcol}{row}'
            if tc not in cells and pc not in cells: continue
            if cells.get(pc)=='--':
                # Published sentinel: keep its exact location as unavailable;
                # do not fabricate a measured value for a supplied duration.
                missing.append((tc,pc,cells.get(tc))); continue
            if not isinstance(cells.get(tc),(int,float)) or not isinstance(cells.get(pc),(int,float)):
                raise ValueError('missing or nonnumeric measurement pair')
            times.append(cells[tc]);values.append(cells[pc]);refs.append((tc,pc))
        if len(times)<3 or np.any(np.diff(times)<=0) or min(times)<=0 or not np.all(np.isfinite(values)):
            raise ValueError('invalid experimental duration curve')
        curves.append(SwitchingCurve(tuple(times),tuple(values),voltage,voltage/6e-9,
            specimen+'; 2% doping; 6 nm; epitaxial LSMO/STO',SOURCE_SHA256,sheets[specimen],tuple(refs),tuple(missing)))
    return tuple(curves)


def switching_fraction(times_s, nominal_field_V_m, *, tau0_s, activation_field_V_m, exponent=1.):
    """Stable Merz-Weibull pulse law; exponent=1 is single-time NLS relaxation."""
    t=np.asarray(times_s)
    if (t.dtype.kind not in 'fiu' or not np.all(np.isfinite(t)) or np.any(t<0)
            or any(isinstance(x,(bool,np.bool_)) or not np.isscalar(x) or not np.isfinite(x) or x<=0
                   for x in (nominal_field_V_m,tau0_s,activation_field_V_m,exponent))):
        raise ValueError('finite positive SI coefficients/field and nonnegative durations required')
    log_t=np.full(t.shape,-np.inf);np.log(t,out=log_t,where=t>0)
    log_power=exponent*(log_t-np.log(tau0_s)-activation_field_V_m/nominal_field_V_m)
    return np.where(t==0,0.,-np.expm1(-np.exp(np.clip(log_power,-745,7))))


def fit_switching_kinetics(training, holdout, *, rmse_budget, max_error_budget, fit_exponent=False):
    """Fit training curves only, evaluate predeclared independent voltage curves.

    Returns failed validation explicitly. A numerical fit is not evidence of
    native device applicability, internal field or absolute P/leakage closure.
    """
    if not training or not holdout or not isinstance(fit_exponent,bool):
        raise ValueError('nonempty training and holdout curve sets required')
    all_curves=tuple(training)+tuple(holdout)
    if not all(isinstance(c,SwitchingCurve) for c in all_curves): raise ValueError('traceable switching curves required')
    for c in all_curves:
        t=np.asarray(c.times_s);y=np.asarray(c.normalized_switched_polarization)
        if (t.dtype.kind not in 'fiu' or y.dtype.kind not in 'fiu' or t.ndim!=1 or t.size<3
                or t.shape!=y.shape or not np.all(np.isfinite(t)) or not np.all(np.isfinite(y))
                or np.any(t<=0) or np.any(np.diff(t)<=0)
                or len(c.source_cells)!=len(t) or len(set(c.source_cells))!=len(t)
                or not isinstance(c.source_sha256,str) or len(c.source_sha256)!=64
                or any(x not in '0123456789abcdef' for x in c.source_sha256)
                or not isinstance(c.specimen,str) or not c.specimen.strip()
                or not isinstance(c.source_sheet,str) or not c.source_sheet.strip()
                or any(not np.isfinite(x) or x<=0 for x in (c.voltage_V,c.nominal_field_V_m))):
            raise ValueError('invalid measured duration curve or missing provenance')
    if len(set(c.voltage_V for c in all_curves))!=len(all_curves):
        raise ValueError('hold out entire independent drive curves without duplicates')
    if len({(c.specimen,c.source_sha256,c.source_sheet) for c in all_curves})!=1:
        raise ValueError('cannot mix specimens or experimental protocols')
    if set(c.voltage_V for c in training)&set(c.voltage_V for c in holdout):
        raise ValueError('hold out entire independent drive curves, not points from a training curve')
    for budget in (rmse_budget,max_error_budget):
        if isinstance(budget,(bool,np.bool_)) or not np.isscalar(budget) or not np.isfinite(budget) or not 0<budget<1:
            raise ValueError('predeclared absolute fraction budgets must lie between 0 and 1')
    def predict(c,x):
        return switching_fraction(c.times_s,c.nominal_field_V_m,tau0_s=np.exp(x[0]),
            activation_field_V_m=x[1]*1e9,exponent=np.exp(x[2]) if fit_exponent else 1.)
    def residual(x):
        return np.concatenate([predict(c,x)-c.normalized_switched_polarization for c in training])
    x0=[-25.,4.] + ([0.] if fit_exponent else [])
    bounds=([-100.,1e-6]+([-3.] if fit_exponent else []),[-5.,40.]+([3.] if fit_exponent else []))
    fit=least_squares(residual,x0,bounds=bounds,xtol=1e-12,ftol=1e-12,gtol=1e-12,max_nfev=2000)
    singular=np.linalg.svd(fit.jac,compute_uv=False)
    identifiable=bool(singular[-1]>0 and singular[0]/singular[-1]<1e8)
    def evaluate(curves):
        reports=[]
        for c in curves:
            prediction=predict(c,fit.x);r=prediction-c.normalized_switched_polarization
            reports.append(dict(voltage_V=c.voltage_V,points=len(r),rmse=float(np.sqrt(np.mean(r*r))),
                max_absolute_error=float(np.max(abs(r))),predicted=prediction.tolist(),
                measured=list(c.normalized_switched_polarization),times_s=list(c.times_s)))
        return reports
    train_report,test_report=evaluate(training),evaluate(holdout)
    passed=bool(fit.success and identifiable and all(r['rmse']<=rmse_budget and
        r['max_absolute_error']<=max_error_budget for r in test_report))
    return dict(tau0_s=float(np.exp(fit.x[0])),activation_field_V_m=float(fit.x[1]*1e9),
        exponent=float(np.exp(fit.x[2])) if fit_exponent else 1.,training=train_report,holdout=test_report,
        rmse_budget=float(rmse_budget),max_error_budget=float(max_error_budget),
        optimizer_converged=bool(fit.success),identifiable=identifiable,holdout_passed=passed,
        jacobian_condition_number=float(singular[0]/singular[-1]) if singular[-1]>0 else None,
        source_sha256=all_curves[0].source_sha256,source=ARTICLE,specimen=all_curves[0].specimen,
        scope='published_normalized_pulse_duration_Merz_Weibull_surrogate',
        native_single_time_law_compatible=not fit_exponent,physical_validated=False,
        dynamic_landau_viscosity_identified=False,internal_field_validated=False)
