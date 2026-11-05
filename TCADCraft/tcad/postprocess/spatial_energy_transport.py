"""SI spatial energy-flux identification and full-profile comparison.

The identified MB law is S=a*k*T*F-b*k^2*n*mu*T*grad(T)/q,
where a=5*r/2 and b=a*hf. Commercial heat flux is kinetic; a native
material-energy flux must first have its band-edge particle flux removed.
"""
import re
import numpy as np
Q=1.602176634e-19;KB=1.380649e-23


def _vector(v,name):
    a=np.asarray(v)
    if (a.dtype.kind not in 'fiu' or a.ndim!=1 or not np.all(np.isfinite(a)) or
            np.any(np.abs(a.astype(np.longdouble))>np.finfo(float).max)):
        raise ValueError(name+' requires a finite real SI vector')
    return np.array(a,dtype=float,copy=True)


def _positive_scalar(value,name):
    a=np.asarray(value)
    if (a.ndim or a.dtype.kind not in 'fiu' or not np.isfinite(a) or
            a<=0 or a>np.finfo(float).max):
        raise ValueError(name+' requires a positive finite real scalar')
    result=float(a)
    if result==0:raise ValueError(name+' is below the float64 range')
    return result


def _coordinates(value,name,minimum):
    x=_vector(value,name)
    if len(x)<minimum or np.any(x[1:]<=x[:-1]):
        raise ValueError(name+' requires ordered spatial points')
    # A finite pair of endpoints need not have a representable difference.
    with np.errstate(over='ignore',invalid='ignore'):
        widths=x[1:]-x[:-1]
    if not np.all(np.isfinite(widths)):
        raise ValueError(name+' interval exceeds finite float64 range')
    if any(np.asarray(v).item()!=0 and z==0 for v,z in zip(value,x)):
        raise ValueError(name+' nonzero coordinate is below the float64 range')
    return x


def _outside_original_bounds(query,reference):
    # Compare exact scalar ratios before a mixed list or float64 cast rounds
    # an out-of-domain integer/extended-precision value onto an endpoint.
    low_num,low_den=np.asarray(reference[0]).item().as_integer_ratio()
    high_num,high_den=np.asarray(reference[-1]).item().as_integer_ratio()
    for value in query:
        num,den=np.asarray(value).item().as_integer_ratio()
        if num*low_den<low_num*den or num*high_den>high_num*den:
            return True
    return False


def validate_spatial_profile(profile):
    if profile.get('role') not in ('calibration','holdout','control') or not isinstance(profile.get('case_id'),str):
        raise ValueError('explicit case and role required')
    if not re.fullmatch('[0-9a-f]{64}',profile.get('source_sha256','')):
        raise ValueError('source SHA256 required')
    if profile.get('units')!='SI' or not profile.get('material_model'):
        raise ValueError('SI units and material identity required')
    x=_coordinates(profile['x_m'],'x',9)
    arrays={}
    for key in ('Tn_K','Tp_K','Tl_K','n_m3','p_m3','mu_n_m2_Vs','mu_p_m2_Vs',
                'Fn_m2_s','Fp_m2_s','Sn_W_m2','Sp_W_m2'):
        a=_vector(profile[key],key)
        if a.shape!=x.shape:raise ValueError('matching spatial field lengths required')
        if key[:2] in ('Tn','Tp','Tl') or key in ('n_m3','p_m3','mu_n_m2_Vs','mu_p_m2_Vs'):
            if np.any(a<=0):raise ValueError('positive temperature/density/mobility required')
        arrays[key]=a
    return x,arrays


def _design(profile,carrier):
    x,v=validate_spatial_profile(profile)
    T=v['Tn_K' if carrier=='electrons' else 'Tp_K']
    n=v['n_m3' if carrier=='electrons' else 'p_m3'];mu=v['mu_n_m2_Vs' if carrier=='electrons' else 'mu_p_m2_Vs']
    F=v['Fn_m2_s' if carrier=='electrons' else 'Fp_m2_s'];S=v['Sn_W_m2' if carrier=='electrons' else 'Sp_W_m2']
    with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
        gradient=np.gradient(T,x,edge_order=2)
        design=np.column_stack((KB*T*F,-KB**2/Q*n*mu*T*gradient))
    # Exclude endpoint reconstruction and its two nearest sampled neighbors.
    keep=slice(2,-2)
    if not np.all(np.isfinite(design[keep])):
        raise ValueError('spatial energy design exceeds finite float64 range')
    return design[keep],S[keep]


def fit_spatial_energy_flux(profiles,*,maximum_condition=100.,relative_gate=.03):
    """Identify coefficients only when every calibration profile fits the law.

    Calibration and holdout errors use the same prespecified relative gate,
    scaled separately by each profile's observed peak. A failed training law
    raises before holdout prediction; a good holdout cannot rescue it.
    """
    profiles=tuple(profiles)
    if not profiles:raise ValueError('spatial profiles required')
    for p in profiles:validate_spatial_profile(p)
    for key in ('case_id','source_sha256'):
        if len({p[key] for p in profiles})!=len(profiles):raise ValueError('duplicate case/source leakage')
    if len({p['material_model'] for p in profiles})!=1:raise ValueError('material identity changed')
    train=[p for p in profiles if p['role']=='calibration'];held=[p for p in profiles if p['role']=='holdout']
    if not train or not held:raise ValueError('independent calibration and holdout profiles required')
    maximum_condition=_positive_scalar(maximum_condition,'maximum condition')
    relative_gate=_positive_scalar(relative_gate,'relative gate')
    if maximum_condition<=1:
        raise ValueError('positive prespecified gates required')
    fits={};betas={};checks=[];calibration_checks=[]
    for carrier in ('electrons','holes'):
        matrices,values=zip(*(_design(p,carrier) for p in train));A=np.vstack(matrices);y=np.concatenate(values)
        norms=np.linalg.norm(A,axis=0)
        if np.any(norms==0):raise ValueError('missing advective or diffusive excitation')
        scaled=A/norms;condition=float(np.linalg.cond(scaled))
        if condition>maximum_condition or np.linalg.matrix_rank(scaled)!=2:
            raise ValueError('spatial energy coefficients are not independently identifiable')
        beta=np.linalg.lstsq(scaled,y,rcond=None)[0]/norms
        if np.any(beta<=0):raise ValueError('unphysical nonpositive identified coefficients')
        fit=dict(r=float(beta[0]/2.5),hf=float(beta[1]/beta[0]),condition=condition,
            calibration_case_ids=[p['case_id'] for p in train],calibration_source_sha256=[p['source_sha256'] for p in train],
            maximum_training_peak_relative_error=float(np.max(np.abs(A@beta-y))/max(np.max(abs(y)),1e-300)))
        fits[carrier]=fit
        betas[carrier]=beta
        for p,B,z in zip(train,matrices,values):
            peak=float(np.max(abs(z)));error=float(np.max(abs(B@beta-z)))
            relative_error=error/max(peak,1e-300)
            passed=bool(np.isfinite(relative_error) and relative_error<=relative_gate)
            calibration_checks.append(dict(case_id=p['case_id'],role='calibration',carrier=carrier,
                source_sha256=p['source_sha256'],maximum_error_W_m2=error,reference_peak_W_m2=peak,
                maximum_peak_relative_error=relative_error,accepted=passed))
            if not passed:
                raise ValueError('calibration spatial energy flux exceeds relative gate: '+p['case_id']+' / '+carrier)
    # Validate both species' training laws before consulting either holdout.
    for carrier,beta in betas.items():
        for p in held:
            B,z=_design(p,carrier);error=float(np.max(abs(B@beta-z))/max(np.max(abs(z)),1e-300))
            checks.append(dict(case_id=p['case_id'],carrier=carrier,maximum_peak_relative_error=error,
                               accepted=bool(error<=relative_gate)))
    return dict(parameters=fits,holdouts=checks,holdouts_accepted=all(c['accepted'] for c in checks),
        calibration_checks=calibration_checks,calibration_accepted=True,accepted=all(c['accepted'] for c in checks),
        commercial_spatial_coefficients_identified=True,experimental_validated=False,physical_validated=False,
        law='S=(5*r/2)*(k*T*F-hf*k^2*n*mu*T*grad(T)/q)',units='SI')


def check_spatial_energy_flux(profiles,coefficients,*,relative_gate=.03,minimum_peak_flux_W_m2=1e-12):
    """Check frozen coefficients against new profiles without estimating parameters.

    Each carrier is scaled by its own observed peak kinetic heat flux. Unresolved
    fluxes cannot qualify the constitutive law. Source hashes identify supplied
    bytes; they do not authenticate commercial or experimental provenance.
    """
    profiles=tuple(profiles)
    if not profiles:raise ValueError('spatial profiles required')
    for p in profiles:validate_spatial_profile(p)
    for key in ('case_id','source_sha256'):
        if len({p[key] for p in profiles})!=len(profiles):raise ValueError('duplicate case/source leakage')
    if len({p['material_model'] for p in profiles})!=1:raise ValueError('material identity changed')
    relative_gate=_positive_scalar(relative_gate,'relative gate')
    minimum_peak_flux_W_m2=_positive_scalar(minimum_peak_flux_W_m2,'minimum peak flux')
    if not isinstance(coefficients,dict) or set(coefficients)!= {'electrons','holes'}:
        raise ValueError('explicit coefficients for both carriers required')
    frozen={}
    for carrier in ('electrons','holes'):
        values=coefficients[carrier]
        if not isinstance(values,dict) or set(values)!= {'r','hf'}:
            raise ValueError('positive finite r and hf required for each carrier')
        frozen[carrier]={k:_positive_scalar(v,carrier+' '+k) for k,v in values.items()}
    betas={}
    for carrier,values in frozen.items():
        advective=_positive_scalar(2.5*values['r'],carrier+' advective coefficient')
        diffusive=_positive_scalar(advective*values['hf'],carrier+' diffusive coefficient')
        betas[carrier]=np.array([advective,diffusive])
    checks=[]
    for p in profiles:
        for carrier,values in frozen.items():
            A,y=_design(p,carrier);peak=float(np.max(abs(y)))
            with np.errstate(over='ignore',under='ignore',invalid='ignore'):
                predicted=A@betas[carrier]
                error=float(np.max(abs(predicted-y)))
            budget=relative_gate*peak
            normalized=error/peak if peak>0 else None
            if (not np.all(np.isfinite(predicted)) or not np.isfinite(error) or
                    not np.isfinite(budget) or (normalized is not None and not np.isfinite(normalized))):
                raise ValueError('spatial energy prediction, error or budget exceeds finite float64 range')
            resolved=peak>=minimum_peak_flux_W_m2
            checks.append(dict(case_id=p['case_id'],role=p['role'],carrier=carrier,
                source_sha256=p['source_sha256'],maximum_error_W_m2=error,reference_peak_W_m2=peak,
                maximum_peak_relative_error=normalized,resolved=bool(resolved),
                accepted=bool(resolved and error<=budget)))
    return dict(parameters=frozen,checks=checks,accepted=all(c['accepted'] for c in checks),
        coefficients_fitted=False,provenance_authenticated=False,experimental_validated=False,
        physical_validated=False,units='SI')


def compare_temperature_profiles(x_m,temperatures,reference,*,bath_K,atol_K=.001,peak_rtol=.1,
                                 minimum_signal_K=.01,require_resolved=False):
    """Compare every cell center using each reference field's own excursion.

    Set require_resolved=True for three-temperature qualification: an accurate
    but unexcited field then fails overall acceptance. The default preserves
    the separate error/resolution diagnostics for general profile comparison.
    All gates and their resulting budgets must be finite real scalars.
    Coordinates must retain finite intervals and their original domain bounds.
    """
    bath_K=_positive_scalar(bath_K,'bath temperature')
    atol_K=_positive_scalar(atol_K,'absolute tolerance')
    peak_rtol=_positive_scalar(peak_rtol,'relative tolerance')
    minimum_signal_K=_positive_scalar(minimum_signal_K,'minimum signal')
    if not isinstance(require_resolved,(bool,np.bool_)):
        raise ValueError('require_resolved must be boolean')
    x=_coordinates(x_m,'cell centers',2);xr,fields=validate_spatial_profile(reference)
    if (x[0]<xr[0] or x[-1]>xr[-1] or
            _outside_original_bounds(x_m,reference['x_m'])):
        raise ValueError('ordered cell centers inside the measured domain required')
    rows={}
    for key in ('Tn_K','Tp_K','Tl_K'):
        a=_vector(temperatures[key],key)
        if a.shape!=x.shape or np.any(a<=0):raise ValueError('matching positive cell temperatures required')
        expected=np.interp(x,xr,fields[key]);signal=float(np.max(abs(fields[key]-bath_K)))
        error=float(np.max(abs(a-expected)));budget=atol_K+peak_rtol*signal
        if not np.isfinite(budget):raise ValueError('temperature error budget exceeds finite float64 range')
        rows[key]=dict(maximum_error_K=error,reference_excursion_K=signal,budget_K=budget,
            resolved=bool(signal>=minimum_signal_K),accepted=bool(error<=budget))
    errors_passed=all(r['accepted'] for r in rows.values())
    resolved=all(r['resolved'] for r in rows.values())
    return dict(accepted=bool(errors_passed and (resolved or not require_resolved)),fields=rows,
                all_temperature_errors_within_budget=errors_passed,resolution_required=bool(require_resolved),
                all_three_temperatures_resolved=resolved,source_sha256=reference['source_sha256'],
                experimental_validated=False,physical_validated=False,provenance_authenticated=False)
