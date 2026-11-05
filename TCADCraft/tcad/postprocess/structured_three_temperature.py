"""Independent material-energy/particle audit for nodal-to-primal initialization."""
from itertools import product
import numpy as np
from .fermi_spectral_energy import reference_reservoir
from tcad.solver.cut_cell_transport import Q


def audit_structured_three_temperature_transfer(grid, old, mesh, new, capacity_node, capacity_cell,
        valleys_n, valleys_p, Ec_J, Eh_J, *, particle_atol, energy_atol_J, charge_atol_C):
    for value in (particle_atol,energy_atol_J,charge_atol_C):
        if isinstance(value,(bool,np.bool_)) or not np.isscalar(value) or not np.isfinite(value) or value<=0:
            raise ValueError('positive absolute transfer budgets required')
    axes=grid.axis_coordinates();shape=tuple(max(1,len(a)-1) for a in axes)
    if len(mesh.volumes_m3)!=np.prod(shape) or len(new.n_m3)!=np.prod(shape):
        raise ValueError('primal cell count does not cover StructuredGrid')
    if old.time_s!=new.time_s:raise ValueError('initialization must not advance physical time')
    cap0=np.broadcast_to(np.asarray(capacity_node,float),(grid.npts(),))
    cap1=np.asarray(capacity_cell,float)
    if (cap1.shape!=(len(mesh.volumes_m3),) or np.any(~np.isfinite(cap0)) or np.any(~np.isfinite(cap1))
            or np.any(cap0<=0) or np.any(cap1<=0)):
        raise ValueError('positive source/target capacities required')
    bbox=((grid.xmin,grid.xmax),(grid.ymin,grid.ymax),(grid.zmin,grid.zmax))
    weights=[]
    for a,(lo,hi) in zip(axes,bbox):
        weights.append(np.array([hi-lo],np.longdouble) if len(a)==1 else
                       (np.r_[np.diff(a),0.]+np.r_[0.,np.diff(a)]).astype(np.longdouble)/2)
    nodal_volumes=(weights[2][:,None,None]*weights[1][None,:,None]*weights[0][None,None,:]).ravel()
    cache={}
    def energies(state,label,valleys,band):
        temperature=state.electron_temperature_K if label=='n' else state.hole_temperature_K
        density=state.n_m3 if label=='n' else state.p_m3
        values=[]
        for n,T in zip(density,temperature):
            key=(label,np.longdouble(n),float(T))
            if key not in cache:cache[key]=reference_reservoir(n,T,band,valleys)['energy_density_J_m3']
            values.append(cache[key])
        return np.asarray(values,np.longdouble)
    u0=np.array([energies(old,'n',valleys_n,Ec_J),energies(old,'p',valleys_p,Eh_J),
                 cap0.astype(np.longdouble)*old.temperature_K])
    u1=np.array([energies(new,'n',valleys_n,Ec_J),energies(new,'p',valleys_p,Eh_J),
                 cap1.astype(np.longdouble)*new.temperature_K])
    particles=[];energy=[];seen=set();geometry=True;capacities=True
    for c,(center,volume) in enumerate(zip(mesh.centroids_m,mesh.volumes_m3)):
        index=[];width=[];options=[]
        for a,x,(lo,hi) in zip(axes,center,bbox):
            if len(a)==1:i=0;left,right=lo,hi;options.append((0,))
            else:
                i=int(np.searchsorted(a,x)-1)
                if not 0<=i<len(a)-1:raise ValueError('target center lies outside source intervals')
                left,right=a[i],a[i+1];options.append((i,i+1))
            index.append(i);width.append(right-left)
            geometry &= abs(x-(left+(right-left)/2)) <= 5e-13*(right-left)
        key=tuple(index)
        if key in seen:raise ValueError('duplicate primal cell')
        seen.add(key)
        expected_volume=np.prod(np.asarray(width,np.longdouble))
        geometry &= abs(np.longdouble(volume)/expected_volume-1)<=5e-13
        # Reconstruct corner indices from physical centers, without production
        # background indices or production averaging/thermodynamic helpers.
        nodes=[grid.index(i,j,k) for i,j,k in product(*options)]
        capacities &= abs(cap1[c]/float(np.mean(cap0[nodes],dtype=np.longdouble))-1)<=2e-14
        particles.append([np.longdouble(volume)*getattr(new,f)[c]-expected_volume*
            np.mean(getattr(old,f)[nodes],dtype=np.longdouble) for f in ('n_m3','p_m3')])
        energy.append(np.longdouble(volume)*u1[:,c]-expected_volume*np.mean(u0[:,nodes],axis=1,dtype=np.longdouble))
    particles=np.asarray(particles,np.longdouble);energy=np.asarray(energy,np.longdouble)
    volumes=mesh.volumes_m3.astype(np.longdouble)
    global_particles=np.array([sum(volumes*getattr(new,f))-sum(nodal_volumes*getattr(old,f))
                               for f in ('n_m3','p_m3')],np.longdouble)
    global_energy=np.sum(volumes*u1,axis=1,dtype=np.longdouble)-np.sum(nodal_volumes*u0,axis=1,dtype=np.longdouble)
    charge=Q*(global_particles[1]-global_particles[0])
    valid=bool(geometry and capacities and np.all(np.isfinite(energy)) and np.all(np.isfinite(particles)) and
        np.max(abs(particles))<=particle_atol and np.max(abs(global_particles))<=particle_atol and
        np.max(abs(energy))<=energy_atol_J and np.max(abs(global_energy))<=energy_atol_J and abs(charge)<=charge_atol_C)
    return dict(valid=valid,scope='multilinear_nodal_particle_and_FD_material_energy_initialization',
        geometry_valid=bool(geometry),capacities_valid=bool(capacities),
        max_cell_particle_error=float(np.max(abs(particles))),global_particle_errors=global_particles.astype(float),
        max_cell_energy_error_J=float(np.max(abs(energy))),global_material_energy_errors_J=global_energy.astype(float),
        charge_error_C=float(charge),physical_time_advanced=False,electrostatic_energy_preserved=False,
        complete_device_energy=False,physical_validated=False)
