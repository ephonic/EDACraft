"""Conservative piecewise-constant projection of exported cubic-LK states.

Conserves each integral P_c dV, not pointwise history or nonlinear energy.
Material interfaces and physical support boundaries must remain fixed.
"""
import numpy as np
from scipy.sparse import csr_matrix


def dual_faces(axes, singleton_widths, zero_d_faces=''):
    if (not isinstance(zero_d_faces, str) or len(set(zero_d_faces)) != len(zero_d_faces)
            or set(zero_d_faces) - set('xXyYzZ')):
        raise ValueError('invalid zero-D face selection')
    if len(axes) != 3 or len(singleton_widths) != 3:
        raise ValueError('three axes and extrusion widths required')
    result = []
    for a, (axis, width) in enumerate(zip(axes, singleton_widths)):
        if np.iscomplexobj(axis): raise ValueError('real axes required')
        x = np.asarray(axis, dtype=float)
        if x.ndim != 1 or not x.size or not np.all(np.isfinite(x)) or np.any(np.diff(x) <= 0):
            raise ValueError('finite increasing axes required')
        if x.size == 1:
            if any(f in zero_d_faces for f in 'xXyYzZ'[2*a:2*a+2]):
                raise ValueError('zero-D faces require active axes')
            if not np.isfinite(width) or width <= 0: raise ValueError('positive extrusion required')
            f = np.array([x[0]-width/2, x[0]+width/2])
        else:
            f = np.r_[x[0], x[:-1]+np.diff(x)/2, x[-1]]
            if 'xXyYzZ'[2*a] in zero_d_faces: f[0] -= (x[1]-x[0])/2
            if 'xXyYzZ'[2*a+1] in zero_d_faces: f[-1] += (x[-1]-x[-2])/2
        if np.any(np.diff(f) <= 0) or not np.all(np.isfinite(f)):
            raise ValueError('dual support cannot be represented')
        result.append(f)
    return result


def _overlap(source, target):
    s, t = (np.asarray(x, dtype=float) for x in (source, target))
    if any(x.ndim != 1 or x.size < 2 or not np.all(np.isfinite(x))
           or np.any(np.diff(x) <= 0) for x in (s, t)):
        raise ValueError('finite increasing cell faces required')
    if not np.array_equal(s[[0,-1]], t[[0,-1]]):
        raise ValueError('physical support boundaries changed')
    rows, cols, data = [], [], []
    i = j = 0
    while i < s.size-1 and j < t.size-1:
        length = min(s[i+1],t[j+1])-max(s[i],t[j])
        if length > 0:
            rows.append(j); cols.append(i); data.append(length/(t[j+1]-t[j]))
        if s[i+1] <= t[j+1]: i += 1
        else: j += 1
    return csr_matrix((data,(rows,cols)),shape=(t.size-1,s.size-1))


def conservative_lk_transfer(polarization, source_faces, target_faces, *,
        source_mask, target_mask, alpha, beta, max_landau_energy_change_J):
    """Return owned (N,3) P and a signed remesh-energy report; SI units.

    This exported-float64 projection is not a bit-exact native checkpoint.
    Caller must budget the nonlinear energy jump before accepting a remesh.
    """
    if len(source_faces) != 3 or len(target_faces) != 3:
        raise ValueError('three face axes required')
    matrices = [_overlap(s,t) for s,t in zip(source_faces,target_faces)]
    ss = tuple(len(f)-1 for f in source_faces)[::-1]
    ts = tuple(len(f)-1 for f in target_faces)[::-1]
    raw = np.asarray(polarization)
    if raw.dtype.kind not in 'fiu' or raw.shape != (int(np.prod(ss)),3):
        raise ValueError('real polarization must have shape (source N,3)')
    p = np.asarray(raw,dtype=float)
    sm, tm = np.asarray(source_mask), np.asarray(target_mask)
    if sm.dtype.kind != 'b' or tm.dtype.kind != 'b' or sm.shape != (p.shape[0],) or tm.shape != (int(np.prod(ts)),):
        raise ValueError('boolean material masks must match each mesh')
    if not np.all(np.isfinite(p)) or np.any(p[~sm] != 0):
        raise ValueError('finite P required and non-FE polarization must be zero')
    if (any(isinstance(v,(bool,np.bool_)) or not np.isscalar(v) or not np.isfinite(v)
            for v in (alpha,beta,max_landau_energy_change_J))
            or beta <= 0 or max_landau_energy_change_J < 0):
        raise ValueError('finite coefficients, beta>0 and nonnegative energy budget required')

    def project(values):
        a = values.reshape(ss + values.shape[1:])
        for axis, matrix in zip((2,1,0),matrices):
            b = np.moveaxis(a,axis,0)
            b = (matrix @ b.reshape(b.shape[0],-1)).reshape((matrix.shape[0],)+b.shape[1:])
            a = np.moveaxis(b,0,axis)
        return a.reshape((int(np.prod(ts)),)+values.shape[1:])

    occupancy = project(sm.astype(float))
    outside = project((~sm).astype(float))
    if np.any(occupancy[~tm] > 0) or np.any(outside[tm] > 0):
        raise ValueError('mixed material support or moved FE interface; remesh rejected')
    out = project(p); out[~tm] = 0

    def volume(faces):
        x,y,z = [np.diff(f).astype(np.longdouble) for f in faces]
        return (z[:,None,None]*y[None,:,None]*x[None,None,:]).ravel()
    sv,tv = volume(source_faces),volume(target_faces)
    old = np.sum(sv[:,None]*p,axis=0)
    new = np.sum(tv[:,None]*out,axis=0)
    scale = np.sum(sv[:,None]*abs(p),axis=0)
    if np.any(abs(new-old) > 128*np.finfo(float).eps*scale):
        raise ValueError('polarization integral failed the conservation budget')
    def energy(v,q):
        q = q.astype(np.longdouble)
        return np.sum(v[:,None]*(np.longdouble(alpha)*q*q/2+np.longdouble(beta)*q**4/4))
    before,after = energy(sv,p),energy(tv,out)
    change = after-before
    if not np.isfinite(change) or abs(change) > max_landau_energy_change_J:
        raise ValueError('Landau remesh energy change exceeds explicit budget')
    return out.copy(), dict(scope='exported_cubic_LK_piecewise_constant_projection',
        source_integral_P_dV_C_m=np.asarray(old,dtype=float).tolist(),
        target_integral_P_dV_C_m=np.asarray(new,dtype=float).tolist(),
        integral_error_C_m=np.asarray(new-old,dtype=float).tolist(),
        source_FE_volume_m3=float(sv[sm].sum()),target_FE_volume_m3=float(tv[tm].sum()),
        landau_energy_before_J=float(before),landau_energy_after_J=float(after),
        remesh_energy_change_J=float(change),max_landau_energy_change_J=float(max_landau_energy_change_J),
        physical_validated=False,bit_exact_checkpoint=False)
