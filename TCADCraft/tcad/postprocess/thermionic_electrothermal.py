"""State-based energy audit plus independent half-cell/thermionic trace checks."""
import numpy as np
from tcad.solver.cut_cell_transport import Q,KB,_array
from tcad.solver.thermionic_electrothermal import ThermionicElectrothermalCutCellTransport
from .electrothermal_energy import audit_electrothermal_cut_cell_energy
from .thermionic_energy import audit_thermionic_interface
from .multivalley_energy import audit_multivalley_interface


def audit_thermionic_electrothermal(model,old,new,report,*,charge_atol_C,particle_atol,energy_atol_J,
                                   particle_flux_atol_s,energy_flux_atol_W,entropy_atol_W_K):
    if not isinstance(model,ThermionicElectrothermalCutCellTransport):raise ValueError('thermionic electrothermal model required')
    base=audit_electrothermal_cut_cell_energy(model,old,new,report,charge_atol_C=charge_atol_C,
        particle_atol=particle_atol,energy_atol_J=energy_atol_J)
    valid=base['valid'] and report.get('thermionic_faces')==list(model.thermionic_faces)
    valid=valid and report.get('state_advanced') is True and report.get('complete_device_energy') is False
    if not isinstance(report.get('thermionic_interfaces'),dict) or set(report['thermionic_interfaces'])!={'electrons','holes'}:
        raise ValueError('thermionic carrier coverage mismatch')
    p=model._poisson(new.n_m3,new.p_m3,new.trap_fraction,charge_atol_C);ld=np.longdouble
    qn,qp=model.quantum_potentials(new.n_m3,new.p_m3)
    i,j,faces=model.ti,model.tj,model.tf;To,Tn=new.temperature_K[i],new.temperature_K[j];dt=new.time_s-old.time_s
    rows={};material=np.zeros(len(faces))
    for label,density,band,mu0,exponent,z,A,fluxkey in (
            ('electrons',new.n_m3,model.Ec,model.mn,model.mn_exponent,-1,model.An,'integrated_electron_particle_flux_s'),
            ('holes',new.p_m3,model.Eh,model.mp,model.mp_exponent,1,model.Ap,'integrated_hole_particle_flux_s')):
        row=report['thermionic_interfaces'][label]
        q=qn if label=='electrons' else qp
        qface=(q[i]+q[j])/2
        effective_band=band+q
        no=_array(row['owner_density_m3'],len(faces),'owner trace',positive=True)
        nn=_array(row['neighbor_density_m3'],len(faces),'neighbor trace',positive=True)
        if label in model.thermionic_valleys:
            given=row['moments']
            records=[]
            keys=('particle_flux_s','forward_particle_rate_s','reverse_particle_rate_s',
                'kinetic_owner_flux_W','kinetic_neighbor_flux_W','material_energy_flux_W',
                'electrochemical_energy_flux_W','lattice_heat_owner_W','lattice_heat_neighbor_W','entropy_production_W_K')
            arrays={key:_array(given[key],len(faces),'reported '+key) for key in keys}
            for k in range(len(faces)):
                scalar={key:arrays[key][k] for key in keys}
                scalar.update({key:given[key] for key in ('statistics','valley_count','complete_device_energy','physical_validated')})
                records.append(audit_multivalley_interface(scalar,no[k],nn[k],To[k],Tn[k],
                    effective_band[i[k]],effective_band[j[k]],model.thermionic_valleys[label],model.ta[k],
                    potential_V=p['face_potential_V'][faces[k]],charge_sign=z,emission_factor=A[k],
                    statistics=model.thermionic_statistics,particle_flux_atol_s=particle_flux_atol_s,
                    energy_flux_atol_W=energy_flux_atol_W,entropy_atol_W_K=entropy_atol_W_K))
            moment=dict(valid=all(r['valid'] for r in records),faces=records)
        else:
            moment=audit_thermionic_interface(row['moments'],no,nn,To,Tn,effective_band[i],effective_band[j],model.masses[label],model.ta,
                potential_V=p['face_potential_V'][faces],charge_sign=z,emission_factor=A,
                particle_flux_atol_s=particle_flux_atol_s,energy_flux_atol_W=energy_flux_atol_W,entropy_atol_W_K=entropy_atol_W_K)
        # Direct extended-precision Bernoulli, independently of the production
        # trace elimination and its small/large-field Bernoulli approximations.
        def half_flux(a,b,T,dphi,metric,mu,qdrop):
            d=(ld(z)*ld(Q)*dphi.astype(ld)+qdrop.astype(ld))/(ld(KB)*T.astype(ld));B=np.ones_like(d);Br=B.copy();nz=d!=0
            B[nz]=d[nz]/np.expm1(d[nz]);Br[nz]=(-d[nz])/np.expm1(-d[nz])
            return mu.astype(ld)*ld(KB)*T.astype(ld)/ld(Q)*metric.astype(ld)*(B*a.astype(ld)-Br*b.astype(ld))
        mu=mu0*(model.T/new.temperature_K)**exponent
        owner=half_flux(density[i],no,To,p['face_potential_V'][faces]-p['cell_potential_V'][i],model.half_owner_metric,mu[i],qface-q[i])
        neighbor=half_flux(nn,density[j],Tn,p['cell_potential_V'][j]-p['face_potential_V'][faces],model.half_neighbor_metric,mu[j],q[j]-qface)
        given=np.asarray(report[fluxkey])[faces];interface=np.asarray(row['moments']['particle_flux_s'])
        errors=np.r_[owner-given,neighbor-given,interface-given]
        maximum=float(np.max(abs(errors),initial=0))
        valid=valid and moment['valid'] and maximum<=particle_flux_atol_s and dt*maximum<=particle_atol
        material+=np.asarray(row['moments']['material_energy_flux_W'])
        rows[label]=dict(moment_audit=moment,max_series_flux_error_s=maximum)
    energy_error=np.asarray(report['integrated_carrier_energy_flux_W'])[faces]-material
    valid=valid and np.max(abs(energy_error),initial=0)<=energy_flux_atol_W and dt*np.max(abs(energy_error),initial=0)<=energy_atol_J
    return dict(valid=bool(valid),energy_audit=base,carriers=rows,interface_energy_flux_error_W=energy_error,
        state_advanced=True,temperature_solved=True,complete_device_energy=False,physical_validated=False)
