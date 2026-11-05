"""Check sampled spatial fields before accepting a uniform-film reference."""
import numpy as np

from tcad.postprocess.terminal_trace import _real_array, _real_scalar


def audit_uniform_ferroelectric_reference(positions_m, polarization_C_m2, *,
        time_s, polarization_scale_C_m2, spread_atol_C_m2, spread_rtol):
    """Check all three P components at explicitly supplied FE sample positions.

    The caller must select FE points from declared material geometry and convert
    coordinates/P to SI. Positions have shape (N, D), D in 1..3; P is (N, 3).
    Every component's max-minus-min spread must be at most atol + rtol*scale.
    A finite nonuniform field returns compatible=False; malformed input raises.

    This only audits supplied samples at time_s. It cannot certify unsampled
    points/times, complete PDE dimensionality, domains, material calibration,
    or physical validity. A compatible field still needs observable comparisons.
    """
    x=_real_array(positions_m,'positions_m')
    p=_real_array(polarization_C_m2,'polarization_C_m2')
    t=_real_scalar(time_s,'time_s')
    scale=_real_scalar(polarization_scale_C_m2,'polarization_scale_C_m2',positive=True)
    atol=_real_scalar(spread_atol_C_m2,'spread_atol_C_m2')
    rtol=_real_scalar(spread_rtol,'spread_rtol')
    if (x.ndim!=2 or x.shape[0]<2 or x.shape[1] not in (1,2,3)
            or p.shape!=(len(x),3) or t<0. or atol<0. or not 0.<=rtol<1.):
        raise ValueError('require N>=2 spatial FE samples, N by 3 P, nonnegative time/atol and 0<=rtol<1')
    # Do not overflow the spread or budget before checking their export range.
    xl=x.astype(np.longdouble);pl=p.astype(np.longdouble)
    with np.errstate(over='ignore',invalid='ignore'):
        extent=xl.max(axis=0)-xl.min(axis=0)
        spread=pl.max(axis=0)-pl.min(axis=0)
        budget=np.longdouble(atol)+np.longdouble(rtol)*np.longdouble(scale)
    bound=np.finfo(float).max
    if (not np.all(np.isfinite(extent)) or not np.all(np.isfinite(spread))
            or not np.isfinite(budget) or np.any(extent>bound)
            or np.any(spread>bound) or budget>bound or (budget!=0 and float(budget)==0.)
            or (budget==0. and rtol>0.)):
        raise ValueError('spatial spread, extent or budget exceeds float64 export range')
    if not np.any(extent>0.):
        raise ValueError('spatial samples must span at least one coordinate')
    return dict(uniform_reference_compatible=bool(np.all(spread<=budget)),
        time_s=t,samples=len(x),sampled_coordinate_dimension=x.shape[1],
        sampled_active_axes=np.flatnonzero(extent>0.).tolist(),
        polarization_spread_C_m2=np.asarray(spread,dtype=float),
        max_polarization_spread_C_m2=float(np.max(spread)),
        spread_budget_C_m2=float(budget),
        polarization_min_C_m2=np.min(p,axis=0).copy(),
        polarization_max_C_m2=np.max(p,axis=0).copy(),
        scope='supplied FE spatial samples at one time; uniform-target compatibility only',
        trajectory_validated=False,physical_validated=False)
