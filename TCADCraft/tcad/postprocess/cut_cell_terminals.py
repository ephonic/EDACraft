"""Named physical terminals over partitions of Dirichlet cut-cell faces."""
from collections.abc import Mapping
import numpy as np
from tcad.solver.cut_cell_transport import Q,_array


def validate_terminal_groups(mesh,dirichlet_V,groups):
    """Own a complete, disjoint, equipotential partition of electrical faces."""
    if not isinstance(groups,Mapping) or not groups:raise ValueError('nonempty terminal groups mapping required')
    if not isinstance(dirichlet_V,Mapping) or not dirichlet_V:raise ValueError('electrical boundary map required')
    used=set();owned={}
    for name,faces in groups.items():
        if not isinstance(name,str) or not name.strip():raise ValueError('nonempty terminal name required')
        if not isinstance(faces,(list,tuple,np.ndarray)) or np.ndim(faces)!=1 or not len(faces):
            raise ValueError('terminal requires a nonempty face sequence')
        ids=[]
        for f in faces:
            if (isinstance(f,(bool,np.bool_)) or not isinstance(f,(int,np.integer))
                    or f not in dirichlet_V or not 0<=f<len(mesh.faces) or mesh.faces[f].neighbor>=0):
                raise ValueError('terminal requires electrical Dirichlet boundary faces')
            f=int(f)
            if f in used:raise ValueError('terminal groups must be disjoint without duplicate faces')
            used.add(f);ids.append(f)
        voltage=dirichlet_V[ids[0]]
        for f in ids:
            if np.ndim(dirichlet_V[f])!=0:raise ValueError('scalar terminal voltage required')
            _array(dirichlet_V[f],1,'terminal voltage')
        if any(dirichlet_V[f]!=voltage for f in ids):raise ValueError('physical terminal must be equipotential')
        owned[name]=tuple(ids)
    if used!=set(dirichlet_V):raise ValueError('terminal groups must cover every electrical Dirichlet face')
    return owned


def integrate_cut_cell_terminals(mesh,dirichlet_V,groups,old_poisson,new_poisson,
                                 electron_flux_s,hole_flux_s,carrier_energy_flux_W,heat_flux_W,dt_s):
    """Reconstruct group currents/work from fields, not reported face currents.

    Positive terminal current enters the device. Particle/heat energy flux is
    positive out of the device. Qelectrode=-Dout uses the solver convention.
    Thermal boundaries outside electrical terminals remain in the global audit.
    """
    groups=validate_terminal_groups(mesh,dirichlet_V,groups);nf=len(mesh.faces)
    dt=float(_array(dt_s,1,'terminal time step',positive=True)[0])
    fn=_array(electron_flux_s,nf,'electron flux');fp=_array(hole_flux_s,nf,'hole flux')
    energy=_array(carrier_energy_flux_W,nf,'carrier energy flux');heat=_array(heat_flux_W,nf,'heat flux')
    da=_array(old_poisson['integrated_D_flux_C'],nf,'old displacement flux')
    db=_array(new_poisson['integrated_D_flux_C'],nf,'new displacement flux')
    ld=np.longdouble;result={}
    for name,ids in groups.items():
        ids=np.array(ids,int);v=float(dirichlet_V[int(ids[0])])
        delta_q=-np.sum(db[ids].astype(ld)-da[ids].astype(ld))
        charge_flux=ld(Q)*np.sum(fp[ids].astype(ld)-fn[ids].astype(ld))
        displacement=delta_q/ld(dt);conduction=-charge_flux
        result[name]=dict(voltage_V=v,area_m2=float(sum(np.linalg.norm(mesh.faces[f].area_vector_m2) for f in ids)),
            charge_before_C=float(-np.sum(da[ids],dtype=ld)),charge_after_C=float(-np.sum(db[ids],dtype=ld)),
            displacement_current_A=float(displacement),conduction_current_A=float(conduction),
            current_A=float(displacement+conduction),source_work_J=float(ld(v)*(delta_q-ld(dt)*charge_flux)),
            outward_carrier_energy_J=float(ld(dt)*np.sum(energy[ids],dtype=ld)),
            outward_heat_J=float(ld(dt)*np.sum(heat[ids],dtype=ld)))
    return result


def audit_named_terminals(expected,given,*,dt_s,charge_atol_C,energy_atol_J):
    """Validate every named quantity with dimensionally appropriate budgets."""
    for name,value in dict(dt_s=dt_s,charge_atol_C=charge_atol_C,energy_atol_J=energy_atol_J).items():
        _array(value,1,name,positive=True)
    if not isinstance(given,dict) or set(given)!=set(expected):raise ValueError('named terminal coverage mismatch')
    errors={};valid=True
    for name,values in expected.items():
        if not isinstance(given[name],dict) or set(given[name])!=set(values):
            raise ValueError('named terminal quantity coverage mismatch')
        errors[name]={}
        for key,value in values.items():
            actual=float(_array(given[name][key],1,'terminal '+key)[0]);error=actual-value
            errors[name][key]=error
            if key.endswith('_A'):okay=abs(dt_s*error)<=charge_atol_C
            elif key.endswith('_C'):okay=abs(error)<=charge_atol_C
            elif key.endswith('_J'):okay=abs(error)<=energy_atol_J
            else:okay=abs(error)<=64*np.finfo(float).eps*max(abs(value),np.finfo(float).tiny)
            valid=bool(valid and okay)
    return dict(valid=valid,errors=errors)
