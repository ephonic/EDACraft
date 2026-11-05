"""Independent equal-mass interface moment audit and steady-device adapter."""
import numpy as np
from tcad.solver.cut_cell_transport import Q,KB,_array
from tcad.physics.thermionic_interface import H,_inputs,thermionic_interface_ledger


def audit_thermionic_interface(report,n_owner_m3,n_neighbor_m3,T_owner_K,T_neighbor_K,band_owner_J,band_neighbor_J,
        mass_kg,area_m2,*,potential_V=0.,charge_sign=-1,emission_factor=2.,
        particle_flux_atol_s,energy_flux_atol_W,entropy_atol_W_K):
    """Check reported moments using direct extended-precision emission rates.

    This audit does not call the production moment implementation. Errors
    have separate number/s, W and W/K budgets. No device energy claim follows.
    """
    for name,v in dict(particle=particle_flux_atol_s,energy=energy_flux_atol_W,entropy=entropy_atol_W_K).items():
        _array(v,1,name,positive=True)
    values=_inputs(n_owner_m3,n_neighbor_m3,T_owner_K,T_neighbor_K,band_owner_J,band_neighbor_J,
        mass_kg,area_m2,potential_V,charge_sign,emission_factor)
    no,nn,To,Tn,bo,bn,m,area,phi,z,A=[v.astype(np.longdouble) for v in values]
    k=np.longdouble(KB);q=np.longdouble(Q);h=np.longdouble(H);high=np.maximum(bo,bn)
    # Deliberately use direct Maxwell rates, not the logarithmic subtraction
    # and factored heat expressions used by the production kernel.
    forward=area*A*np.sqrt(k*To/(2*np.longdouble(np.pi)*m))*no*np.exp(-(high-bo)/(k*To))
    reverse=area*A*np.sqrt(k*Tn/(2*np.longdouble(np.pi)*m))*nn*np.exp(-(high-bn)/(k*Tn))
    particle=forward-reverse
    ko=forward*(high-bo+2*k*To)-reverse*(high-bo+2*k*Tn)
    kn=forward*(high-bn+2*k*To)-reverse*(high-bn+2*k*Tn)
    material=bo*particle+ko;total=material+z*q*phi*particle
    uo=bo+np.longdouble(1.5)*k*To;un=bn+np.longdouble(1.5)*k*Tn
    No=2*(2*np.longdouble(np.pi)*m*k*To/h**2)**np.longdouble(1.5)
    Nn=2*(2*np.longdouble(np.pi)*m*k*Tn/h**2)**np.longdouble(1.5)
    muo=bo+k*To*np.log(no/No);mun=bn+k*Tn*np.log(nn/Nn)
    entropy=(material-mun*particle)/Tn-(material-muo*particle)/To
    expected=dict(particle_flux_s=particle,forward_particle_rate_s=forward,reverse_particle_rate_s=reverse,
        kinetic_owner_flux_W=ko,kinetic_neighbor_flux_W=kn,material_energy_flux_W=material,
        electrochemical_energy_flux_W=total,lattice_heat_owner_W=uo*particle-material,
        lattice_heat_neighbor_W=material-un*particle,entropy_production_W_K=entropy)
    if not isinstance(report,dict) or set(report)!=set(expected):raise ValueError('interface moment coverage mismatch')
    errors={};valid=True
    for name,target in expected.items():
        raw=np.asarray(report[name])
        if raw.dtype.kind not in 'fiu' or raw.shape!=target.shape or not np.all(np.isfinite(raw)):
            raise ValueError('invalid reported '+name)
        error=raw.astype(np.longdouble)-target
        errors[name]=float(np.max(abs(error),initial=0))
        budget=particle_flux_atol_s if name.endswith('_s') else entropy_atol_W_K if name.endswith('_W_K') else energy_flux_atol_W
        valid=valid and errors[name]<=budget
    return dict(valid=bool(valid),max_errors=errors,complete_device_energy=False)


def audit_thermionic_ledger(ledger,n_owner_m3,n_neighbor_m3,T_owner_K,T_neighbor_K,band_owner_J,band_neighbor_J,
        mass_kg,area_m2,dt_s,*,potential_V=0.,charge_sign=-1,emission_factor=2.,
        particle_flux_atol_s,energy_flux_atol_W,entropy_atol_W_K,energy_atol_J):
    """Check each integrated entry, including compensated false heat/storage."""
    _array(energy_atol_J,1,'energy budget',positive=True)
    values=_inputs(n_owner_m3,n_neighbor_m3,T_owner_K,T_neighbor_K,band_owner_J,band_neighbor_J,
        mass_kg,area_m2,potential_V,charge_sign,emission_factor)
    dt=np.asarray(dt_s)
    if dt.dtype.kind not in 'fiu' or np.any(~np.isfinite(dt)) or np.any(dt<=0):raise ValueError('positive time interval required')
    try:dt=np.broadcast_to(dt,values[0].shape).astype(np.longdouble)
    except ValueError:raise ValueError('invalid time interval shape') from None
    audit=audit_thermionic_interface(ledger['flux'],*values[:8],potential_V=values[8],charge_sign=values[9],
        emission_factor=values[10],particle_flux_atol_s=particle_flux_atol_s,energy_flux_atol_W=energy_flux_atol_W,
        entropy_atol_W_K=entropy_atol_W_K)
    no,nn,To,Tn,bo,bn,*_=values;k=np.longdouble(KB)
    transfer=dt*np.asarray(ledger['flux']['particle_flux_s'],dtype=np.longdouble)
    owner=-transfer*(bo.astype(np.longdouble)+np.longdouble(1.5)*k*To.astype(np.longdouble))
    neighbor=transfer*(bn.astype(np.longdouble)+np.longdouble(1.5)*k*Tn.astype(np.longdouble))
    carrier=transfer*((bn.astype(np.longdouble)-bo.astype(np.longdouble))+np.longdouble(1.5)*k*(Tn.astype(np.longdouble)-To.astype(np.longdouble)))
    qo=dt*np.asarray(ledger['flux']['lattice_heat_owner_W'],dtype=np.longdouble)
    qn=dt*np.asarray(ledger['flux']['lattice_heat_neighbor_W'],dtype=np.longdouble)
    expected=dict(transferred_particles=transfer,carrier_storage_owner_J=owner,carrier_storage_neighbor_J=neighbor,
        carrier_storage_total_J=carrier,lattice_heat_owner_J=qo,lattice_heat_neighbor_J=qn,
        entropy_produced_J_K=dt*np.asarray(ledger['flux']['entropy_production_W_K'],dtype=np.longdouble),
        local_energy_residual_J=carrier+qo+qn)
    error={};valid=audit['valid']
    for name,target in expected.items():
        raw=np.asarray(ledger[name])
        if raw.dtype.kind not in 'fiu' or raw.shape!=target.shape or not np.all(np.isfinite(raw)):raise ValueError('invalid ledger '+name)
        error[name]=float(np.max(abs(raw.astype(np.longdouble)-target),initial=0))
        budget=float(np.max(dt))*particle_flux_atol_s if name=='transferred_particles' else (
            float(np.max(dt))*entropy_atol_W_K if name=='entropy_produced_J_K' else energy_atol_J)
        valid=valid and error[name]<=budget
    valid=valid and float(np.max(abs(carrier+qo+qn),initial=0))<=energy_atol_J
    valid=valid and ledger['state_advanced'] is False and ledger['complete_device_energy'] is False and ledger['physical_validated'] is False
    return dict(valid=bool(valid),moment_audit=audit,entry_errors=error,
        max_local_energy_residual_J=float(np.max(abs(carrier+qo+qn),initial=0)),complete_device_energy=False)


def steady_device_interface_energy(model,result,dt_s,*,charge_atol_C,particle_flux_atol_s,current_atol_A,
                                    energy_flux_atol_W,entropy_atol_W_K,energy_atol_J):
    """Evaluate calorimetry on accepted isothermal device traces, without mutation.

    Requires equal DOS masses and the Maxwell emission velocities for EVERY
    configured interface. Arbitrary user-supplied transfer velocities, unequal
    DOS masses and non-isothermal devices are explicitly rejected.
    """
    from tcad.solver.heterojunction_cut_cell import IsothermalHeterojunctionDevice
    if not isinstance(model,IsothermalHeterojunctionDevice):raise ValueError('isothermal heterojunction device required')
    device_audit=model.audit(result,charge_atol_C=charge_atol_C,particle_flux_atol_s=particle_flux_atol_s,current_atol_A=current_atol_A)
    if not device_audit['valid']:raise ValueError('device interface calorimetry requires accepted fields and currents')
    faces=model.operator.interfaces;i=np.array([model.mesh.faces[f].owner for f in faces],int)
    j=np.array([model.mesh.faces[f].neighbor for f in faces],int)
    area=np.array([np.linalg.norm(model.mesh.faces[f].area_vector_m2) for f in faces]);rows={}
    for label,dos,band,z,velocities in (('electrons',model.Nc,model.Ec,-1,model.vn),('holes',model.Nv,model.Eh,1,model.vp)):
        masses=H**2/(2*np.pi*KB*model.T)*(dos/2)**(2/3)
        if not np.allclose(masses[i],masses[j],rtol=2e-13,atol=0):raise ValueError('equal DOS masses required for interface energy moments')
        speed=2*np.sqrt(KB*model.T/(2*np.pi*masses[i]))
        if not np.allclose(velocities,speed,rtol=2e-13,atol=0):raise ValueError('Maxwell emission velocity required for interface energy moments')
        given=result[label];no=given['interface_owner_density_m3'];nn=given['interface_neighbor_density_m3']
        phi=result['poisson']['face_potential_V'][list(faces)]
        ledger=thermionic_interface_ledger(no,nn,model.T,model.T,band[i],band[j],masses[i],area,dt_s,potential_V=phi,charge_sign=z)
        audit=audit_thermionic_ledger(ledger,no,nn,model.T,model.T,band[i],band[j],masses[i],area,dt_s,potential_V=phi,charge_sign=z,
            particle_flux_atol_s=particle_flux_atol_s,energy_flux_atol_W=energy_flux_atol_W,entropy_atol_W_K=entropy_atol_W_K,energy_atol_J=energy_atol_J)
        error=float(np.max(abs(ledger['flux']['particle_flux_s']-np.asarray(given['flux'])[list(faces)]),initial=0))
        if not audit['valid'] or error>particle_flux_atol_s:raise ValueError('interface energy/current consistency failed')
        rows[label]=dict(ledger=ledger,audit=audit,max_device_particle_flux_error_s=error)
    return dict(valid=True,interfaces=list(faces),carriers=rows,scope='isothermal_device_trace_calorimetry',
        temperature_solved=False,state_advanced=False,complete_device_energy=False,physical_validated=False)
