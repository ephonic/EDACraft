"""Explicit conservative migration from StructuredGrid nodes to primal cells."""
from copy import deepcopy
from itertools import product
import numpy as np
from scipy.optimize import brentq
from tcad.mesh.polyhedral_regions import region_cut_cells
from tcad.physics.native_fermi_local import native_fermi_reservoirs
from tcad.physics.fermi_spectral import validate_valleys,valley_dos
from .cut_cell_transport import Q,_array
from .three_temperature import ThreeTemperatureState,ThreeTemperatureElectrothermal
from .device_three_temperature import DeviceThreeTemperature


class StructuredThreeTemperatureDevice(DeviceThreeTemperature):
    @property
    def migration_report(self):
        return deepcopy(self._migration_report)

    def _decorate_report(self,report):
        report.update(device_mesh_mode='StructuredGrid_primal_cells',
                      legacy_StructuredGrid_three_temperature_integrated=True,legacy_run_three_temperature_replaced=False)
        report['missing_physics'].remove('legacy_StructuredGrid_three_temperature_conversion')


def migrate_structured_three_temperature(source,old,*,valleys_n,valleys_p,Ec_J,Eh_J,heat_capacity_J_m3_K,
        relaxation_time_n_s,relaxation_time_p_s,charge_atol_C,particle_atol,energy_atol_J,
        relaxation_law_n=None,relaxation_law_p=None,intercarrier_conductance_W_m3_K=0.,
        pair_generation_rate_m3_s=0.,pair_generation_kinetic_n_J=0.,pair_generation_kinetic_p_J=0.):
    grid=source.mesh;axes=grid.axis_coordinates();nn=grid.npts()
    for name,value in (('charge',charge_atol_C),('particle',particle_atol),('energy',energy_atol_J)):
        _array(value,1,name+' transfer budget',positive=True)
    conductance=float(_array(intercarrier_conductance_W_m3_K,1,
                            'fixed intercarrier conductance',nonnegative=True)[0])
    generation={name:float(_array(value,1,'constant '+name,nonnegative=True)[0]) for name,value in (
        ('pair_generation_rate_m3_s',pair_generation_rate_m3_s),
        ('pair_generation_kinetic_n_J',pair_generation_kinetic_n_J),
        ('pair_generation_kinetic_p_J',pair_generation_kinetic_p_J))}
    if not isinstance(old,ThreeTemperatureState) or not np.isfinite(old.time_s) or old.time_s<0:
        raise ValueError('explicit nodal ThreeTemperatureState with nonnegative finite clock required')
    for field in ('n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K','trap_fraction'):
        a=np.asarray(getattr(old,field))
        if a.shape!=(nn,) or np.any(~np.isfinite(a)) or np.any(a<0):raise ValueError('invalid nodal '+field)
        if field in ('n_m3','p_m3') and np.any(a<=0):raise ValueError('positive nodal density required')
        if 'temperature' in field and (np.any(a<=1) or np.any(a>=1e5)):raise ValueError('nodal temperature out of bounds')
    if np.any(old.trap_fraction<=0) or np.any(old.trap_fraction>=1):raise ValueError('nodal trap fraction must lie strictly inside (0,1)')
    counts=tuple(max(1,len(a)-1) for a in axes);nc=int(np.prod(counts))
    nf=sum((counts[a]+1)*int(np.prod([counts[b] for b in range(3) if b!=a])) for a in range(3))
    if nc*5>1024 or nc+nf>512:raise ValueError('StructuredGrid migration exceeds native dense limits')
    if getattr(source,'_contact_workfunctions',{}) or getattr(source,'_schottky_contact_models',{}):
        raise ValueError('Schottky contacts are outside StructuredGrid migration scope')
    if getattr(source,'_pending_contact_ramps',{}) or getattr(source,'_transient_contact_waveforms',None) is not None:
        raise ValueError('pending contact ramps and transient waveforms are outside fixed-boundary migration scope')
    seed=source._sim.structured_three_temperature_seed()
    bbox=((grid.xmin,grid.xmax),(grid.ymin,grid.ymax),(grid.zmin,grid.zmax))
    for a,positions,spacing,(lo,hi) in zip(axes,[seed[k+'_positions'] for k in 'xyz'],seed['spacings'],bbox):
        native=np.asarray(positions,float) if len(positions) else np.arange(len(a))*spacing
        if (native.shape!=a.shape or not np.allclose(native-native[0],a-a[0],rtol=2e-14,atol=2e-14*(hi-lo)) or
                (len(a)==1 and not np.isclose(spacing,hi-lo,rtol=2e-14,atol=0))):
            raise ValueError('native positions disagree with StructuredGrid coordinates')
    nodal={name:_array(seed[name],nn,name,positive=name not in ('doping_m3','Eg_eV'))
           for name in ('epsilon','mu_n','mu_p','doping_m3','Nc_m3','Nv_m3','Eg_eV','conductivity')}
    T,ambient=_array(seed['temperature_ambient_K'],2,'native temperatures',positive=True)
    vn=validate_valleys(valleys_n);vp=validate_valleys(valleys_p)
    bands=[float(_array(v,1,'fixed band')[0]) for v in (Ec_J,Eh_J)]
    if not np.allclose(nodal['Eg_eV'],sum(bands)/Q,rtol=2e-12,atol=1e-14):
        raise ValueError('fixed target bands must match native bandgap')
    for name,valleys in (('Nc_m3',vn),('Nv_m3',vp)):
        dos=sum(valley_dos(T,valleys)*np.exp(-np.array([v.band_offset_owner_J for v in valleys])/(1.380649e-23*T)))
        if not np.allclose(nodal[name],dos,rtol=2e-12,atol=0):
            raise ValueError('explicit global valleys must match native reference DOS')
    cap0=_array(heat_capacity_J_m3_K,nn,'nodal heat capacity',positive=True)
    tau=[float(_array(v,1,'fixed energy relaxation time',positive=True)[0])
         for v in (relaxation_time_n_s,relaxation_time_p_s)]
    # Primal faces are source nodes on active axes. A singleton is a full
    # extruded interval; its lone sample is constant through that dimension.
    mesh=region_cut_cells([a if len(a)>1 else np.array(b) for a,b in zip(axes,bbox)],{'box':[[]]})
    corners=np.array([[grid.index(i,j,k) for i,j,k in product(*[
        (int(index[a]),int(index[a])+1) if len(axes[a])>1 else (0,) for a in range(3)])]
        for index in mesh.background_indices],int)
    mean=lambda v:np.mean(np.asarray(v,np.longdouble)[corners],axis=1,dtype=np.longdouble)
    cap1=np.asarray(mean(cap0),float)
    density=[mean(old.n_m3),mean(old.p_m3)]
    temperatures=[]
    for n0,T0,n1,band,valleys in ((old.n_m3,old.electron_temperature_K,density[0],bands[0],vn),
                                 (old.p_m3,old.hole_temperature_K,density[1],bands[1],vp)):
        u0=np.array([v['energy_density_J_m3'] for v in native_fermi_reservoirs(n0,T0,np.full(nn,band),valleys)])
        targets=mean(u0);result=[]
        for n,u in zip(n1,targets):
            def residual(t):return native_fermi_reservoirs([n],[t],[band],valleys)[0]['energy_density_J_m3']-float(u)
            result.append(brentq(residual,1.000001,99999.999999,xtol=1e-10,rtol=2e-15))
        temperatures.append(np.array(result))
    state=ThreeTemperatureState(*density,np.asarray(mean(old.trap_fraction),float),
        np.asarray(mean(cap0.astype(np.longdouble)*old.temperature_K)/cap1,float),old.time_s,*temperatures)
    def boundary(name):
        a=np.asarray(seed[name],float)
        if a.ndim!=1 or len(a)%2 or np.any(~np.isfinite(a)):raise ValueError('invalid native '+name)
        out={}
        for index,value in a.reshape(-1,2):
            if index!=int(index) or not 0<=index<nn or int(index) in out:raise ValueError('invalid native boundary index')
            out[int(index)]=value
        return out
    maps={key:boundary(key) for key in ('phi_bc','n_bc','p_bc','thermal_bc')}
    planes={};flat=grid.flat_coords();used=set()
    for name in source._contact_voltages:
        raw=np.asarray(grid.fields['contact_'+name])
        if raw.size!=nn or np.any(~np.isin(raw,[0,1])):raise ValueError('invalid named contact mask')
        mask=raw.astype(bool).ravel();matches=[]
        for axis in range(3):
            if len(axes[axis])==1:continue
            for side in (0,1):
                if np.array_equal(mask,flat[axis]==axes[axis][0 if side==0 else -1]):matches.append((axis,side))
        if len(matches)!=1 or matches[0] in planes:raise ValueError('complete unambiguous named terminal planes required')
        planes[matches[0]]=name;used.update(np.flatnonzero(mask))
    if not planes or set(maps['phi_bc'])!=used or any(not set(maps[k])<=used for k in ('n_bc','p_bc','thermal_bc')):
        raise ValueError('native boundary maps contain uncovered/partial/interior contacts')
    groups={name:[] for name in planes.values()};bc={};contacts={};bath={}
    from .electrothermal_cut_cell import CarrierReservoir
    def constant(nodes,mapping,required=False):
        values=[mapping[i] for i in nodes if i in mapping]
        if not values and not required:return None
        if len(values)!=len(nodes) or any(v!=values[0] for v in values):
            raise ValueError('uniform complete face boundary values required')
        return values[0]
    for f,face in enumerate(mesh.faces):
        if face.neighbor>=0:continue
        axis=int(np.argmax(abs(face.area_vector_m2)));side=int(face.area_vector_m2[axis]>0)
        if (axis,side) not in planes:continue
        name=planes[axis,side];groups[name].append(f)
        nodes=[i for i in corners[face.owner] if flat[axis][i]==axes[axis][0 if side==0 else -1]]
        bc[f]=constant(nodes,maps['phi_bc'],True)
        n=constant(nodes,maps['n_bc']);p=constant(nodes,maps['p_bc'])
        if (n is None)!=(p is None):raise ValueError('both carrier reservoir densities must be specified')
        if n is not None:contacts[f]=CarrierReservoir(n,p,T)
        value=constant(nodes,maps['thermal_bc']) if maps['thermal_bc'] else ambient
        if value is not None:bath[f]=value
    model=ThreeTemperatureElectrothermal(mesh,permittivity_F_m=np.asarray(mean(nodal['epsilon']),float),
        mobility_n_m2_Vs=np.asarray(mean(nodal['mu_n']),float),mobility_p_m2_Vs=np.asarray(mean(nodal['mu_p']),float),
        mobility_temperature_exponent_n=0.,mobility_temperature_exponent_p=0.,
        fixed_charge_C_m3=np.asarray(mean(nodal['doping_m3'])*np.longdouble(Q),float),temperature_K=T,
        Ec_J=bands[0],Eh_J=bands[1],valleys_n=vn,valleys_p=vp,dirichlet_V=bc,particle_contacts=contacts,
        heat_bath_K=bath,terminal_groups=groups,heat_capacity_J_m3_K=cap1,
        thermal_conductivity_W_m_K=np.asarray(mean(nodal['conductivity']),float),
        relaxation_time_n_s=tau[0],relaxation_time_p_s=tau[1],
        relaxation_law_n=relaxation_law_n,relaxation_law_p=relaxation_law_p,
        intercarrier_conductance_W_m3_K=conductance,**generation)
    from tcad.postprocess.structured_three_temperature import audit_structured_three_temperature_transfer
    audit=audit_structured_three_temperature_transfer(grid,old,mesh,state,cap0,cap1,vn,vp,*bands,
        particle_atol=particle_atol,energy_atol_J=energy_atol_J,charge_atol_C=charge_atol_C)
    if not audit['valid']:raise ValueError('independent StructuredGrid material transfer audit failed: '+str(audit))
    device=StructuredThreeTemperatureDevice(model,state)
    device._migration_report=dict(valid=True,audit=audit,source_nodes=nn,target_cells=nc,
        source_shape=grid.shape(),target_shape=counts,cell_corner_nodes=corners,
        terminal_faces=groups,native_seed=deepcopy(seed),projection='multilinear_material_energy_conservative',
        electrostatic_initialization='new_HMM_Poisson',physical_time_advanced=False,
        legacy_StructuredGrid_three_temperature_integrated=True,legacy_run_three_temperature_replaced=False)
    return device
