"""Conservative remapping of a single compact non-LK ensemble.

The existing native models have one shared branch/kinetic state per FE mask.
Refinement replicates this state; coarsening cannot merge distinct histories.
"""
from copy import deepcopy
import numpy as np
from .conservative_transfer import conservative_lk_transfer


def conservative_ensemble_transfer(state, source_faces, target_faces, *, target_mask):
    if not isinstance(state,dict) or state.get('schema')!='compact_FE_ensemble_v1':
        raise ValueError('versioned compact ensemble history required')
    params=np.asarray(state['parameters']);sm=np.asarray(state['mask']);tm=np.asarray(target_mask)
    p=np.asarray(state['polarization']);play=np.asarray(state['play'])
    if (params.shape!=(10,) or params[0] not in (1,2,3) or sm.dtype.kind!='b'
            or tm.dtype.kind!='b' or not np.any(sm) or not np.any(tm)
            or p.shape!=(sm.size,3) or not np.all(np.isfinite(p))):
        raise ValueError('invalid compact ensemble state')
    model=int(params[0]);n=sm.size;nt=tm.size
    if not np.all(p[sm]==p[sm][0]) or np.any(p[~sm]!=0):
        raise ValueError('cannot merge incompatible ensemble polarization histories')
    blocks=2 if model==3 else 1 if model==1 else 0
    if ((model==1 and play.shape!=(n,)) or (model==2 and play.shape!=(0,))
            or (model==3 and (play.ndim!=1 or play.size<2*n+4 or (play.size-2*n)%2))
            or not np.all(np.isfinite(play))):
        raise ValueError('invalid ensemble memory layout')
    memory=[]
    for b in range(blocks):
        part=play[b*n:(b+1)*n]
        if not np.all(part[sm]==part[sm][0]) or np.any(part[~sm]!=0):
            raise ValueError('cannot merge incompatible ensemble branch histories')
        memory.append(np.where(tm,part[sm][0],0.))
    if model==3:memory.append(play[2*n:].copy())
    # Reuse strict overlap/material-support and integral checks. Dummy quartic
    # coefficients are only an internal geometry check, never physical energy.
    _,geometry=conservative_lk_transfer(p,source_faces,target_faces,
        source_mask=sm,target_mask=tm,alpha=0.,beta=1.,max_landau_energy_change_J=np.finfo(float).max)
    out=deepcopy(state);out['mask']=tm.copy();out['polarization']=np.zeros((nt,3))
    out['polarization'][tm]=p[sm][0]
    out['play']=np.concatenate(memory) if memory else np.empty(0)
    report={k:v for k,v in geometry.items() if k in (
        'source_integral_P_dV_C_m','target_integral_P_dV_C_m','integral_error_C_m',
        'source_FE_volume_m3','target_FE_volume_m3')}
    # Report the replicated state actually returned, including rounding.
    x,y,z=[np.diff(f).astype(np.longdouble) for f in target_faces]
    volume=(z[:,None,None]*y[None,:,None]*x[None,None,:]).ravel()
    integral=np.sum(volume[:,None]*out['polarization'],axis=0)
    sx,sy,sz=[np.diff(f).astype(np.longdouble) for f in source_faces]
    sv=(sz[:,None,None]*sy[None,:,None]*sx[None,None,:]).ravel()
    original=np.sum(sv[:,None]*p,axis=0)
    tolerance=128*np.finfo(float).eps*np.sum(sv[:,None]*abs(p),axis=0)
    if np.any(abs(integral-original)>tolerance):
        raise ValueError('replicated ensemble failed polarization integral conservation')
    report['target_integral_P_dV_C_m']=np.asarray(integral,float).tolist()
    report['integral_error_C_m']=(integral-original).astype(float).tolist()
    report.update(scope='compact_non_LK_single_ensemble_conservative_replication',model=model,
        turning_point_pairs=(play.size-2*n)//2 if model==3 else 0,
        physical_validated=False,bit_exact_checkpoint=False,remesh_energy_available=False)
    return out,report
