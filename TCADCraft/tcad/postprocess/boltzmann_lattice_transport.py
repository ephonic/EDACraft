"""Independent exact replay of a frozen Fourier stage on complete MB states."""
from fractions import Fraction
from .boltzmann_recomputed_transport import (_decode,_take,_wire,_values,point,saved_state,scaled_value_fraction,moment_wire)
from .boltzmann_scaled_arithmetic import _tokens,_count
from .boltzmann_scaled_collision_trace import _multiply
from .boltzmann_dyadic_quotient import quotient
from .boltzmann_product_range import _binary113,_vector
from .boltzmann_scaled_split import ALPHA,EPS,_command,_display,_metadata,_saved_fingerprint
from .boltzmann_recomputed_endpoint_split import audit_mb_recomputed_endpoint_split,exchange_budget


def _packet(raw,name,n,start):
    _tokens(raw,60000)
    if tuple(raw[:2])!=(name,'113'):raise ValueError('lattice proof version/precision')
    result=[];parts=[];j=start
    for k in range(n):
        p,j=_take(raw,j);x=scaled_value_fraction(p)
        if _wire(x)!=p:raise ValueError('lattice noncanonical partition')
        result.append(x);parts.append(p)
    return result,parts,j


def face_values(raw):
    v,parts,j=_packet(raw,'mb_lattice_face_v1',5,3)
    if j!=len(raw) or 1+sum(int(p[2]) for p in parts)>4096:raise ValueError('lattice face coverage/budget')
    G=_vector(raw[2:3])[0]
    if G<=0:raise ValueError('positive lattice conductance required')
    return G,v,parts


def _temperature(endpoint):
    f,v=_decode(endpoint);q,r=quotient(v[0],f[3])
    return f[2]+q,r


def audit_mb_lattice_face(owner,neighbor,geometry,raw,*,bath_temperature_K=None):
    a=point(owner);g=list(map(lambda x:_binary113(_command(x)),geometry))
    bath=bath_temperature_K is not None
    if len(g)!=5 or min(g[0],g[1],g[3],g[4])<=0 or (g[2]!=0 if bath else g[2]<=0):raise ValueError('lattice geometry/boundary kind')
    G=_binary113(g[0]/_binary113(_binary113(g[1]/g[3])+_binary113(g[2]/g[4])))
    Ta,ra=_temperature(owner)
    if bath:
        if neighbor is not None:raise ValueError('thermal bath has no endpoint neighbor')
        Tb=_binary113(_command(bath_temperature_K));rb=Fraction();actualTb=Tb
        if not 1<Tb<100000:raise ValueError('thermal bath domain')
    else:
        b=point(neighbor);Tb,rb=_temperature(neighbor);actualTb=b['Tl']
    expected=[Ta,ra,Tb,rb,_multiply(G,Ta-Tb)]
    actual,v,parts=face_values(raw)
    if actual!=G or v!=expected:raise ValueError('lattice Fourier graph or exact remainder mismatch')
    error=v[4]-G*(a['Tl']-actualTb);bound=4096*EPS*G*(abs(a['Tl'])+abs(actualTb))
    if abs(error)>bound:raise ValueError('lattice physical Fourier flux bound exceeded')
    return dict(valid=True,actual_temperature_remainders_checked=True,physical_fourier_error_W=_display(error),physical_fourier_bound_W=_display(bound),native_physics_used=False,physical_validated=False)


def split_lattice_cell(raw):
    v,parts,j=_packet(raw,'mb_lattice_cell_v1',7,3);endpoint,j=_take(raw,j,60000)
    if j!=len(raw):raise ValueError('lattice cell trailing data')
    f,w=_decode(endpoint)
    evidence=sum(int(p[2]) for p in parts)+sum(int(_wire(x)[2]) for x in w)
    if _count(raw[2],4096)!=evidence:raise ValueError('lattice cell evidence count')
    return endpoint,v


def _cell(old,new,raw,moments,dt,ea):
    before=point(old);after=point(new);f=before['frame'];g,w=_decode(new);_,v=_decode(old)
    endpoint,proof=split_lattice_cell(raw)
    J=sum((sign*_multiply(flux,dt) for sign,flux in moments),Fraction())
    L,rV=quotient(J,f[4]);alpha=_binary113(Fraction(3,2)*_binary113(ALPHA/Fraction(3,2)))
    qn,rn=quotient(_multiply(_multiply(alpha,f[0]),L),f[3]);qp,rp=quotient(_multiply(_multiply(alpha,f[1]),L),f[3])
    if list(new)!=endpoint or proof!=[J,L,rV,-qn,rn,-qp,rp]:raise ValueError('lattice cell provenance/quotient/remainder mismatch')
    expected=v.copy()
    for k,x in ((0,L),(5,-qn),(6,-qp)):expected[k]+=x
    if g!=f or w!=expected:raise ValueError('lattice stage changed unrelated coordinates or lost compensation')
    V=f[4];carrier=[V*(after['K'][k]-before['K'][k]) for k in (0,1)];lattice=V*f[3]*(after['Tl']-before['Tl'])
    residual=[V*(after['n'][k]-before['n'][k]) for k in (0,1)]+carrier+[lattice-J,sum(carrier)+lattice-J]
    scale=abs(J)+V*abs(L)*(1+ALPHA*(f[0]+f[1])/f[3])
    budget=min(ea,4096*EPS*scale);budgets=[Fraction(),Fraction(),budget,budget,budget,budget]
    if any(abs(x)>y for x,y in zip(residual,budgets)):raise ValueError('lattice actual carrier/lattice/total energy gate failed')
    check=dict(valid=True,exact_volume_and_compensation_remainders_checked=True,carrier_energy_preserved_within_rounding_budget=True,residuals=list(map(_display,residual)),budgets=list(map(_display,budgets)))
    return check,residual,budgets


def _topology(states,faces):
    if not 1<=len(states)<=256 or len(faces)>512:raise ValueError('bounded lattice topology required')
    edges=set()
    for face in faces:
        bath='bath_temperature_K' in face
        if set(face)!=({'owner','bath_temperature_K','geometry'} if bath else {'owner','neighbor','geometry'}):raise ValueError('explicit lattice topology required')
        i=face['owner'];j=None if bath else face['neighbor']
        if type(i) is not int or not 0<=i<len(states) or (not bath and (type(j) is not int or not 0<=j<len(states) or i==j)):raise ValueError('lattice face index')
        if not bath:
            edge=tuple(sorted((i,j)))
            if edge in edges:raise ValueError('duplicate lattice internal face')
            edges.add(edge)
        yield i,j,bath


def _stage(old,new,report,faces,dt_s,energy_atol_J):
    old=tuple(map(saved_state,old));new=tuple(map(saved_state,new));dt=_binary113(_command(dt_s));ea=min(_command(energy_atol_J),Fraction(1,10**27))
    if min(dt,ea)<=0 or len(new)!=len(old):raise ValueError('positive lattice exposure and matching cells required')
    topology=list(_topology(old,faces));n=len(old)
    if any(s.time_s!=old[0].time_s or s.physical_clock!=old[0].physical_clock for s in old):raise ValueError('synchronized lattice stage clocks required')
    _metadata(report,dict(scope='complete_endpoint_frozen_Fourier_stage',execution_backend='native',precision_bits=113,exposure_dt_s=float(dt_s),old_sha256=list(map(_saved_fingerprint,old)),new_sha256=list(map(_saved_fingerprint,new)),physical_time_advanced=False,lattice_flux_included=True,field_work_included=False,complete_device_energy=False,physical_validated=False))
    if len(report['faces'])!=len(faces) or len(report['cells'])!=n:raise ValueError('lattice stage proof coverage')
    moments=[[] for s in old];rates=[Fraction() for s in old];signed=[Fraction() for s in old];outward=Fraction();checks=[]
    for spec,(i,j,bath),raw in zip(faces,topology,report['faces']):
        check=audit_mb_lattice_face(old[i].endpoint,None if bath else old[j].endpoint,spec['geometry'],raw,bath_temperature_K=spec['bath_temperature_K'] if bath else None);checks.append(check)
        G,values,parts=face_values(raw);flux=values[4];value=_multiply(flux,dt)
        moments[i].append((-1,flux));signed[i]-=value;rates[i]+=G
        if bath:outward+=value
        else:moments[j].append((1,flux));signed[j]+=value;rates[j]+=G
    totals=[Fraction()]*6;totalbudgets=[Fraction()]*6;cells=[];cellbudgets=[]
    for i,(a,b) in enumerate(zip(old,new)):
        if a.time_s!=b.time_s or list(a.physical_clock)!=list(b.physical_clock):raise ValueError('lattice operator stage must preserve physical clock')
        f=point(a.endpoint)['frame'];cfl=dt*rates[i]/(f[3]*f[4])
        if cfl>1:raise ValueError('explicit lattice CFL exceeds one')
        check,r,budget=_cell(a.endpoint,b.endpoint,report['cells'][i],moments[i],dt,ea/n)
        check['cfl']=_display(cfl);cells.append(check);cellbudgets.append(budget[-1])
        totals=[x+y for x,y in zip(totals,r)];totalbudgets=[x+y for x,y in zip(totalbudgets,budget)]
    totalbudgets=[min(ea,x) for x in totalbudgets]
    if any(abs(x)>y for x,y in zip(totals,totalbudgets)):raise ValueError('lattice global energy gate failed')
    check=dict(valid=True,faces=checks,cells=cells,global_residuals=list(map(_display,totals)),global_budgets=list(map(_display,totalbudgets)),outward_bath_heat_J=_display(outward),internal_heat_faces_cancelled=True,explicit_CFL_checked=True,physical_clock_preserved=True,native_physics_used=False,complete_device_energy=False,physical_validated=False)
    return check,signed,cellbudgets


def audit_mb_lattice_stage(old,new,report,*,faces,dt_s,energy_atol_J=1e-27):
    return _stage(old,new,report,faces,dt_s,energy_atol_J)[0]


def audit_mb_conducting_endpoint_split(configurations,old,new,report,*,faces,thermal_faces,dt_s,impulses_J=None,energy_atol_J=1e-27):
    old=tuple(map(saved_state,old));new=tuple(map(saved_state,new));n=len(old);ea=min(_command(energy_atol_J),Fraction(1,10**27));dt=_binary113(_command(dt_s))
    if len(new)!=n or not n or ea<=0 or dt<=0:raise ValueError('conducting split coverage/budget')
    middle=tuple(map(saved_state,report['pre_lattice_states']));base=report['carrier_split']
    _metadata(report,dict(scope='complete_endpoint_transport_collision_lattice_Lie_split',execution_backend='native',precision_bits=113,temporal_order=1,autonomous_operators_only=True,monolithic_coupled_BE=False,dt_s=float(dt_s),old_sha256=list(map(_saved_fingerprint,old)),new_sha256=list(map(_saved_fingerprint,new)),physical_time_advanced=True,lattice_flux_included=True,field_work_included=False,complete_device_energy=False,physical_validated=False))
    checked=audit_mb_recomputed_endpoint_split(configurations,old,middle,base,faces=faces,dt_s=dt_s,impulses_J=impulses_J,energy_atol_J=energy_atol_J/2)
    heat,signed_heat,heatbudgets=_stage(middle,new,report['lattice'],thermal_faces,dt_s,energy_atol_J/2)
    q=[(0.,0.,0.) for s in old] if impulses_J is None else impulses_J
    signed=[[Fraction()]*4 for s in old];scales=[[Fraction()]*4 for s in old]
    for spec,row in zip(faces,base['transport']['transfers']):
        values,ps,j=_values(moment_wire(row['raw']),'mb_scaled_moments_v1',4)
        for k,x in enumerate(values):
            value=_multiply(x,dt);i=spec['owner'];signed[i][k]-=value;scales[i][k]+=abs(value)
            if 'neighbor' in spec:signed[spec['neighbor']][k]+=value;scales[spec['neighbor']][k]+=abs(value)
    totals=[Fraction()]*6;globalbudgets=[Fraction()]*6;cells=[]
    for i,(a,b) in enumerate(zip(old,new)):
        before=point(a.endpoint);after=point(b.endpoint);f=before['frame'];V=f[4]
        if list(b.physical_clock)!=_wire(scaled_value_fraction(a.physical_clock)+dt):raise ValueError('conducting split physical clock must advance once')
        dN=[V*(after['n'][k]-before['n'][k]) for k in (0,1)]
        dU=[V*(after['K'][k]-before['K'][k]+f[5+k]*(after['n'][k]-before['n'][k])) for k in (0,1)]
        dL=V*f[3]*(after['Tl']-before['Tl']);imp=list(map(_command,q[i]))
        mid=base['transported_states'][i];c=base['collisions'][i];exchange,cb=exchange_budget(mid['endpoint'],c['command'],c['root_packet'])
        r=[dN[k]-signed[i][k] for k in (0,1)]+[dU[k]-signed[i][2+k]+exchange[k]-imp[k] for k in (0,1)]
        r.extend((dL-sum(exchange)-imp[2]-signed_heat[i],sum(dU)+dL-sum(signed[i][2:])-sum(imp)-signed_heat[i]))
        tb=[min(Fraction(1,10**9) if k<2 else _command(energy_atol_J/4),4096*EPS*x) for k,x in enumerate(scales[i])];hb=heatbudgets[i]
        budget=[*tb[:2],min(ea,tb[2]+cb+hb),min(ea,tb[3]+cb+hb),min(ea,cb+hb),min(ea,sum(tb[2:])+cb+hb)]
        if any(abs(x)>y for x,y in zip(r,budget)):raise ValueError('conducting complete interval physical energy gate failed')
        totals=[x+y for x,y in zip(totals,r)];globalbudgets=[x+y for x,y in zip(globalbudgets,budget)]
        cells.append(dict(residuals=list(map(_display,r)),budgets=list(map(_display,budget))))
    globalbudgets=[min(Fraction(1,10**9) if k<2 else ea,x) for k,x in enumerate(globalbudgets)]
    if any(abs(x)>y for x,y in zip(totals,globalbudgets)):raise ValueError('conducting split global physical energy gate failed')
    return dict(valid=True,carrier_split=checked,lattice=heat,cells=cells,whole_interval_particle_energy_closed=True,row_order=['electron_particles','hole_particles','electron_energy','hole_energy','lattice_energy','total_energy'],global_residuals=list(map(_display,totals)),global_budgets=list(map(_display,globalbudgets)),physical_clock_advanced_once=True,thermal_bath_and_carrier_contact_ownership_checked=True,native_physics_used=False,complete_device_energy=False,physical_validated=False)
