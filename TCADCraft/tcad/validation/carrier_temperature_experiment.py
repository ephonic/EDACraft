"""Qualify measured carrier/lattice data before any three-temperature claim.

A publication's 'three-temperature model' may mean electron/optical-phonon/
acoustic-phonon baths. Those observables cannot be relabeled Tn/Tp/Tl.
Numerical and pixel-digitization errors do not replace measurement uncertainty.
"""
import re
import numpy as np


def _real_vector(value):
    """Validate both the supplied data and the representation used to compare."""
    raw=np.asarray(value)
    if raw.ndim!=1 or raw.dtype.kind not in 'fiu' or not np.all(np.isfinite(raw)):
        raise ValueError('finite real vector required')
    with np.errstate(over='ignore',under='ignore',invalid='ignore'):
        converted=np.array(raw,dtype=float,copy=True)
    if not np.all(np.isfinite(converted)) or np.any((raw!=0)&(converted==0)):
        raise ValueError('representable real vector required')
    return converted


def _coordinates(value,minimum):
    coordinate=_real_vector(value)
    # Subtraction in an integer dtype can wrap. Ordering must also survive the
    # float64 conversion that numpy.interp uses; never sort a measured clock.
    if len(coordinate)<minimum or np.any(coordinate[1:]<=coordinate[:-1]):
        raise ValueError('strictly ordered representable coordinates required')
    with np.errstate(over='ignore'):
        widths=coordinate[1:]-coordinate[:-1]
    if not np.all(np.isfinite(widths)):
        raise ValueError('representable interpolation intervals required')
    return coordinate


def _positive_scalar(value,name):
    raw=np.asarray(value)
    if raw.ndim or raw.dtype.kind not in 'fiu' or not np.isfinite(raw) or raw<=0:
        raise ValueError('positive finite '+name+' required')
    with np.errstate(over='ignore',under='ignore',invalid='ignore'):
        converted=np.asarray(raw,dtype=float).item()
    if not np.isfinite(converted) or converted<=0:
        raise ValueError('representable '+name+' required')
    return converted


def _confidence_factor(record):
    factor=_positive_scalar(record['coverage_factor'],'coverage factor')
    level=_positive_scalar(record['confidence_level'],'confidence level')
    if level>=1:raise ValueError('confidence level below one required')
    return factor


def _standard_uncertainty(sigma,factor):
    with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
        standard=sigma if factor is None else sigma/factor
    if np.any(~np.isfinite(standard)) or np.any(standard<=0):
        raise ValueError('representable positive measurement standard uncertainty required')
    return standard


def _outside_original_bounds(measured,predicted):
    """Compare original numeric values without mixed-dtype rounding.

    Even a Python/NumPy mixed signed/unsigned or longdouble comparison can
    project an integer onto a floating endpoint. Exact integer ratios retain
    the original represented coordinates on every NumPy platform.
    """
    # Convert one scalar at a time. Coercing a whole Python list can round its
    # large integers to float64 before the original-bound check even begins.
    low_num,low_den=np.asarray(predicted[0]).item().as_integer_ratio()
    high_num,high_den=np.asarray(predicted[-1]).item().as_integer_ratio()
    for value in measured:
        num,den=np.asarray(value).item().as_integer_ratio()
        if num*low_den<low_num*den or num*high_den>high_num*den:return True
    return False


def qualify_carrier_temperature_experiment(dataset):
    """Return explicit missing evidence; never certify a simulator by metadata."""
    if not isinstance(dataset,dict):raise ValueError('dataset mapping required')
    reasons=[]
    if dataset.get('source_kind')!='measured':reasons.append('source_is_not_measurement')
    if not re.fullmatch('[0-9a-f]{64}',str(dataset.get('source_sha256',''))):reasons.append('original_source_hash_missing')
    if not dataset.get('source_url'):reasons.append('primary_source_missing')
    if not dataset.get('geometry_material_contacts'):reasons.append('device_contract_missing')
    if dataset.get('coordinate_units') not in ('m','s'):reasons.append('physical_coordinate_units_missing')
    observable=dataset.get('observables',{})
    if not isinstance(observable,dict):raise ValueError('observable mapping required')
    coverage={}
    for key in ('electron_temperature_K','hole_temperature_K','lattice_temperature_K'):
        record=observable.get(key);valid=True
        if not isinstance(record,dict):valid=False;reasons.append(key+':not_measured')
        else:
            factor=None
            if record.get('provenance')!='measured':valid=False;reasons.append(key+':not_measurement')
            if record.get('uncertainty_kind') not in ('standard_uncertainty','confidence_interval'):
                valid=False;reasons.append(key+':measurement_uncertainty_missing')
            if record.get('uncertainty_kind')=='confidence_interval':
                try:
                    factor=_confidence_factor(record)
                except (KeyError,TypeError,ValueError):
                    valid=False;reasons.append(key+':confidence_interval_definition_missing')
            try:
                coordinate=_coordinates(record['coordinates'],3)
                value=_real_vector(record['values_K']);sigma=_real_vector(record['uncertainty_K'])
                if coordinate.shape!=value.shape or sigma.shape!=value.shape or np.any(value<=0) or np.any(sigma<=0):
                    raise ValueError('ordered physical measurements with positive uncertainty required')
                _standard_uncertainty(sigma,factor)
            except (KeyError,TypeError,ValueError):valid=False;reasons.append(key+':numeric_data_or_uncertainty_unavailable')
        coverage[key]=valid
    roles=dataset.get('whole_condition_roles',[])
    if not isinstance(roles,(list,tuple)) or 'calibration' not in roles or 'holdout' not in roles:
        reasons.append('independent_whole_condition_holdout_missing')
    return dict(ready_for_three_temperature_acceptance=not reasons,reasons=reasons,observable_coverage=coverage,
        experimental_validated=False,physical_validated=False,
        qualification_only=True,solver_prediction_compared=False)



def compare_carrier_temperature_experiment(dataset,prediction,*,maximum_absolute_error_K,
        maximum_standardized_error,calibration_condition_ids,calibration_source_sha256):
    """Compare a frozen prediction with one independent measured holdout.

    Linear interpolation is in the supplied physical coordinate, without
    extrapolation or fitted offsets. Standardized errors use measurement
    standard uncertainty only (CI half-width divided by its supplied coverage
    factor). Correlations and model/parameter uncertainties are not estimated.
    Passing this numerical comparison does not authenticate supplied metadata
    or certify physical/experimental validity.
    """
    absolute=_positive_scalar(maximum_absolute_error_K,'absolute temperature gate')
    standardized=_positive_scalar(maximum_standardized_error,'standardized gate')
    qualification=qualify_carrier_temperature_experiment(dataset)
    result=dict(qualification=qualification,solver_prediction_compared=False,comparison_passed=False,
        provenance_authenticated=False,experimental_validated=False,physical_validated=False,
        uncertainty_assumption='pointwise measurement standard uncertainty only; no correlation or model covariance',
        interpolation='linear in physical coordinate; no extrapolation')
    if not qualification['ready_for_three_temperature_acceptance']:return result
    if not isinstance(prediction,dict):raise ValueError('prediction mapping required')
    identity=dataset.get('condition_id')
    if not isinstance(identity,str) or not identity or dataset.get('condition_role')!='holdout':
        raise ValueError('independent whole-condition measured holdout required')
    ids=calibration_condition_ids;hashes=calibration_source_sha256
    if (not isinstance(ids,(tuple,list)) or not ids or any(not isinstance(x,str) or not x for x in ids)
            or not isinstance(hashes,(tuple,list)) or not hashes
            or any(not re.fullmatch('[0-9a-f]{64}',str(x)) for x in hashes)):
        raise ValueError('explicit calibration identities and source hashes required')
    if identity in ids or dataset['source_sha256'] in hashes:raise ValueError('calibration/holdout leakage')
    if prediction.get('condition_id')!=identity or prediction.get('coordinate_units')!=dataset['coordinate_units']:
        raise ValueError('prediction condition/coordinate mismatch')
    if prediction.get('geometry_material_contacts')!=dataset['geometry_material_contacts']:
        raise ValueError('prediction device contract mismatch')
    if (not re.fullmatch('[0-9a-f]{64}',str(prediction.get('configuration_sha256','')))
            or prediction.get('configuration_frozen_before_holdout') is not True):
        raise ValueError('declared previously frozen configuration required')
    fields={}
    for key,measured in dataset['observables'].items():
        if key not in qualification['observable_coverage']:continue
        candidate=prediction.get('observables',{}).get(key)
        if not isinstance(candidate,dict):raise ValueError('all three predicted temperatures required')
        try:
            x=_coordinates(candidate['coordinates'],2);y=_real_vector(candidate['values_K'])
            if x.shape!=y.shape or np.any(y<=0):
                raise ValueError('ordered positive prediction vectors required')
        except (KeyError,TypeError,ValueError) as e:raise ValueError('invalid prediction '+key) from e
        target=_coordinates(measured['coordinates'],3)
        if (_outside_original_bounds(measured['coordinates'],candidate['coordinates'])
                or np.any(target<x[0]) or np.any(target>x[-1])):
            raise ValueError('measurement outside prediction coordinate range')
        with np.errstate(over='ignore',under='ignore',invalid='ignore'):
            values=np.interp(target,x,y)
        if np.any(~np.isfinite(values)) or np.any(values<=0):raise ValueError('unrepresentable temperature interpolation')
        errors=values-_real_vector(measured['values_K'])
        sigma=_standard_uncertainty(_real_vector(measured['uncertainty_K']),
            _confidence_factor(measured) if measured['uncertainty_kind']=='confidence_interval' else None)
        with np.errstate(over='ignore'):
            peak=float(np.max(abs(errors)));z=float(np.max(abs(errors)/sigma))
        fields[key]=dict(predicted_at_measurement_K=values.tolist(),signed_errors_K=errors.tolist(),
            measurement_standard_uncertainty_K=sigma.tolist(),maximum_absolute_error_K=peak,
            maximum_standardized_error=z,passed=bool(peak<=absolute and z<=standardized))
    result.update(solver_prediction_compared=True,comparison_passed=all(f['passed'] for f in fields.values()),
        condition_id=identity,source_sha256=dataset['source_sha256'],configuration_sha256=prediction['configuration_sha256'],
        gates=dict(maximum_absolute_error_K=absolute,maximum_standardized_error=standardized),fields=fields)
    return result
