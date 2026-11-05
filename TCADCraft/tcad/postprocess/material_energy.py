"""Whole restricted-device energy closure with native material half edges."""
import numpy as np

from tcad.mesh.conservative_transfer import dual_faces
from tcad.validation.ferroelectric_energy import audit_ferroelectric_device_energy
from .lk_energy import audit_transient_lk_energy
from .terminal_trace import _real_array


def material_half_edge_quadrature(history, axes_m, singleton_widths_m,
                                  permittivity_F_m, *, zero_d_faces=''):
    """Reconstruct E separately in both materials sharing each FV edge.

    Uses the exact harmonic-epsilon native FV law, including zero-D outer
    half cells. Assumes no edge epsilon overrides or cut-cell operator.
    """
    faces=dual_faces(axes_m,singleton_widths_m,zero_d_faces)
    axes=[np.asarray(x,dtype=np.longdouble) for x in axes_m]
    shape=tuple(map(len,axes));count=int(np.prod(shape))
    xyz=np.array([(i,j,k) for k in range(shape[2]) for j in range(shape[1]) for i in range(shape[0])])
    eps=_real_array(permittivity_F_m,'permittivity').astype(np.longdouble)
    if eps.shape!=(count,) or np.any(eps<=0): raise ValueError('positive nodal epsilon required')
    if not isinstance(history,(tuple,list)) or len(history)<2: raise ValueError('initial state and intervals required')
    phi=_real_array([s['phi'] for s in history],'phi').astype(np.longdouble)
    p=_real_array([s['P'] for s in history],'P').astype(np.longdouble)
    if phi.shape!=(len(history),count) or p.shape!=(len(history),3*count):
        raise ValueError('native state shape does not match geometry')
    p=p.reshape(len(history),count,3)
    widths=[np.diff(f).astype(np.longdouble) for f in faces]
    volume=np.prod([w[xyz[:,a]] for a,w in enumerate(widths)],axis=0)
    fields=[];weights=[];dielectrics=[]
    strides=(1,shape[0],shape[0]*shape[1])
    for i,coord in enumerate(xyz):
        for a in range(3):
            area=volume[i]/widths[a][coord[a]]
            if coord[a]+1<shape[a]:
                j=i+strides[a];h=axes[a][coord[a]+1]-axes[a][coord[a]]
                e=2*eps[i]*eps[j]/(eps[i]+eps[j])
                d=e*((phi[:,i]-phi[:,j])/h+(p[:,i,a]/eps[i]+p[:,j,a]/eps[j])/2)
                for q in (i,j):
                    fields.append((d-p[:,q,a])/eps[q]);weights.append(h*area/2);dielectrics.append(eps[q])
            for side in (0,1):
                if ('xXyYzZ'[2*a+side] in zero_d_faces and coord[a]==(shape[a]-1 if side else 0)):
                    h=axes[a][-1]-axes[a][-2] if side else axes[a][1]-axes[a][0]
                    fields.append(-p[:,i,a]/eps[i]);weights.append(h*area/2);dielectrics.append(eps[i])
    return p,volume,(np.array(fields).T,np.array(weights),np.array(dielectrics))


def audit_material_device_energy(history, axes_m, singleton_widths_m,
        permittivity_F_m, *, zero_d_faces='', space_charge_free,
        boundary_coverage_complete, energy_scale_J, lk_field_scale_V_m,
        charge_scale_C, **budgets):
    """Close source, dielectric/Landau storage, LK loss and signed BE terms.

    Public audit for fixed-grid coupled material-LK without mobile/fixed/trap
    charge, leakage, thermal, gradient, quantum, extra depolarization or imprint.
    Geometry/epsilon and absent space charge are explicit caller declarations;
    no unsupported component is silently zeroed. This is not general energy
    closure for arbitrary semiconductor transport or physical validation.
    """
    if not isinstance(space_charge_free,(bool,np.bool_)) or not space_charge_free:
        raise ValueError('explicit space_charge_free=True required for this model')
    local=audit_transient_lk_energy(history)
    for s in history:
        if not s.get('lk_coupled',False) or not s.get('lk_material_field',False) or s.get('lk_substepping',False):
            raise ValueError('requires coupled material LK without hidden substeps')
    params=np.asarray(history[0]['lk_parameters'])
    if params[3]!=0 or params[4]!=0: raise ValueError('imprint/extra depolarization not included')
    p,volume,quadrature=material_half_edge_quadrature(history,axes_m,singleton_widths_m,
        permittivity_F_m,zero_d_faces=zero_d_faces)
    mask=np.asarray(history[0]['lk_node_volumes_m3'])>0
    for s in history:
        if not np.allclose(s['lk_node_volumes_m3'],np.where(mask,volume,0),rtol=1e-12,atol=0):
            raise ValueError('energy geometry does not match native LK volumes')
    report=audit_ferroelectric_device_energy([s['time_s'] for s in history],
        np.array([np.column_stack([s['Ex'],s['Ey'],s['Ez']]) for s in history]),
        p,volume,permittivity_F_m,mask,*params[:3],
        [s['electrode_voltages_V'] for s in history],[s['electrode_charges_C'] for s in history],
        boundary_coverage_complete=boundary_coverage_complete,converged=True,
        energy_scale_J=energy_scale_J,lk_field_scale_V_m=lk_field_scale_V_m,
        charge_scale_C=charge_scale_C,dielectric_quadrature=quadrature,
        electrode_charge_increments_C=[s['electrode_charge_increments_C'] for s in history[1:]],**budgets)
    report['native_local_lk_audit']=local
    report['valid']=report['valid'] and local['valid']
    report['energy_balance_validated']=report['valid']
    report['dielectric_quadrature']='material_half_edges_and_explicit_zero_D_outer_halves'
    report['geometry_coverage_verified']=False
    report['unavailable_components']=['mobile_carrier_free_energy_and_heat',
        'trap_capture_emission_energy','thermal_storage_and_heat_flux',
        'quantum_energy','domain_gradient_energy','leakage_and_breakdown_heat']
    return report
