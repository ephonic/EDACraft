"""Descriptive signed four-corner increments; no acceptance thresholds."""
import numpy as np
FIELDS=('phi_V','Fn_eV','Fp_eV','trap_occupancy','dielectric_phi_V')
def mixed_increment(a,b,c,d,scale):
    a,b,c,d=[np.asarray(x) for x in (a,b,c,d)]
    if not (a.shape==b.shape==c.shape==d.shape) or not all(np.all(np.isfinite(x)) for x in (a,b,c,d)):
        raise ValueError('Four corners require identical shapes and finite values')
    if not np.isfinite(scale) or scale<=0:raise ValueError('Positive finite scale required')
    ds0=b-a;ds1=d-c;dt0=c-a;dt1=d-b
    mixed=ds1-ds0
    np.testing.assert_allclose(mixed,dt1-dt0,rtol=0.,atol=16*np.finfo(mixed.dtype).eps*max(1.,*(float(np.max(abs(x))) for x in (a,b,c,d))))
    norm=lambda x:float(np.max(abs(x)))
    return dict(spatial_at_coarse_dt=norm(ds0),spatial_at_fine_dt=norm(ds1),temporal_at_coarse_y=norm(dt0),temporal_at_fine_y=norm(dt1),
        mixed_absolute=norm(mixed),mixed_normalized=norm(mixed)/scale,array_shape=list(a.shape),compared_values=a.size)
def project(record,reference):
    if len(record['checkpoints'])!=4:raise ValueError('Four full phases required')
    output={}
    for phase,row in enumerate(record['checkpoints']):
        if abs(row['result']['time_s']-20e-12*phase)>=1e-24:raise ValueError('Wrong observation time')
        indices=[]
        for key in ('x_m','y_m','z_m'):
            axis=np.asarray(row[key]);support=np.asarray(reference[key]);idx=np.array([np.argmin(abs(axis-v)) for v in support])
            np.testing.assert_array_equal(axis[idx],support)
            if len(set(idx))!=len(idx):raise ValueError('Support is not nested')
            indices.append(idx)
        ix,iy,iz=indices
        for key in FIELDS:
            array=np.asarray(row['result'][key]);expected=(len(row['z_m']),len(row['y_m']),len(row['x_m'])) if key=='dielectric_phi_V' else (len(row['y_m']),len(row['x_m']))
            if array.shape!=expected:raise ValueError('Unexpected field layout')
            output[str(phase)+'_'+key]=array[np.ix_(iz,iy,ix)] if key=='dielectric_phi_V' else array[np.ix_(iy,ix)]
    return output
