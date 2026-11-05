"""Independent weak-collision split, Fourier and accounted-rounding audits.

The sealed arithmetic and energy gates are retained under new interval scopes.
Only collision packets use the separately versioned finite weak branch.
"""
from fractions import Fraction
from .boltzmann_scaled_split import ALPHA, EPS, _command, _display, _metadata, _saved_fingerprint
from .boltzmann_recomputed_transport import point, _wire, scaled_value_fraction, saved_state, audit_mb_scaled_transport, moment_wire, _values
from .boltzmann_product_range import _binary113
from .boltzmann_scaled_collision_trace import _multiply
from .boltzmann_weak_endpoint_collision import configuration, exchange_budget, audit_mb_weak_endpoint_collision
from .boltzmann_recomputed_lattice_transport import _stage
from .boltzmann_accounted_rounding import _rounding

def audit_mb_weak_endpoint_split(configurations,old,new,report,*,faces,dt_s,impulses_J=None,
                            particle_atol=1e-9,energy_atol_J=1e-27,number_atol_s=1e-6,energy_atol_W=1e-15):
    old=tuple(map(saved_state,old));new=tuple(map(saved_state,new));n=len(old)
    dt,pa,ea=map(_command,(dt_s,particle_atol,energy_atol_J))
    if min(dt,pa,ea)<=0 or not 1<=n<=256 or len(new)!=n or len(configurations)!=n:raise ValueError('complete endpoint split coverage/budget')
    cfg=[configuration(c) for c in configurations];q=[(0.,0.,0.) for s in old] if impulses_J is None else impulses_J
    if len(q)!=n or any(len(row)!=3 for row in q):raise ValueError('complete endpoint split impulse coverage')
    impulses=[list(map(_command,row)) for row in q]
    _metadata(report,dict(scope='weak_complete_endpoint_same_interval_Lie_split',execution_backend='native',precision_bits=113,
        method='full_density_scaled_transport_then_collision_BE',temporal_order=1,autonomous_operators_only=True,
        stage_clock_model='exact_scaled_auxiliary_then_project',dt_s=float(dt_s),physical_time_advanced=True,
        configuration_sha256=[digest for c,digest in cfg],old_sha256=list(map(_saved_fingerprint,old)),new_sha256=list(map(_saved_fingerprint,new)),
        monolithic_coupled_BE=False,lattice_flux_included=False,field_work_included=False,complete_device_energy=False,physical_validated=False))
    if len(report['transported_states'])!=n or len(report['collision_states'])!=n or len(report['collisions'])!=n:raise ValueError('complete endpoint split proof coverage')
    middle=tuple(map(saved_state,report['transported_states']));aux=tuple(map(saved_state,report['collision_states']))
    transport=audit_mb_scaled_transport(old,middle,report['transport'],faces=faces,dt_s=dt_s,
        particle_atol=particle_atol,energy_atol_J=energy_atol_J/2,number_atol_s=number_atol_s,energy_atol_W=energy_atol_W)
    end=scaled_value_fraction(old[0].physical_clock)+_binary113(dt)
    if report['physical_interval_clock']!=[list(old[0].physical_clock),_wire(end)]:raise ValueError('complete endpoint split physical interval provenance')
    signed=[[Fraction()]*4 for s in old];scales=[[Fraction()]*4 for s in old];boundary=[Fraction()]*4
    for spec,row in zip(faces,report['transport']['transfers']):
        values,ps,j=_values(moment_wire(row['raw']),'mb_scaled_moments_v1',4)
        for k,x in enumerate(values):
            value=x*_binary113(dt);i=spec['owner'];signed[i][k]-=value;scales[i][k]+=abs(value)
            if 'reservoir' in spec:boundary[k]+=value
            else:signed[spec['neighbor']][k]+=value;scales[spec['neighbor']][k]+=abs(value)
    cells=[];children=[];totals=[Fraction()]*6;global_budgets=[Fraction()]*6
    for i,(config,a,b,mid,child) in enumerate(zip(configurations,old,new,middle,aux)):
        checked=audit_mb_weak_endpoint_collision(config,mid,child,report['collisions'][i],dt_s=dt_s,impulses_J=q[i],energy_atol_J=energy_atol_J/(2*n));children.append(checked)
        if b.endpoint!=child.endpoint or list(b.physical_clock)!=_wire(end) or b.time_s!=float(end):raise ValueError('complete endpoint split auxiliary clock projection mismatch')
        before=point(a.endpoint);after=point(b.endpoint);f=before['frame'];V=f[4]
        dN=[V*(after['n'][k]-before['n'][k]) for k in (0,1)]
        dU=[V*(after['K'][k]-before['K'][k]+f[5+k]*(after['n'][k]-before['n'][k])) for k in (0,1)]
        dL=V*f[3]*(after['Tl']-before['Tl'])
        exchange,cb=exchange_budget(mid.endpoint,report['collisions'][i]['command'],report['collisions'][i]['root_packet'])
        r=[dN[k]-signed[i][k] for k in (0,1)]+[dU[k]-signed[i][2+k]+exchange[k]-impulses[i][k] for k in (0,1)]
        r.extend((dL-sum(exchange)-impulses[i][2],sum(dU)+dL-sum(signed[i][2:])-sum(impulses[i])))
        tb=[min(pa if k<2 else _command(energy_atol_J/2),4096*EPS*x) for k,x in enumerate(scales[i])]
        budgets=[*tb[:2],min(ea,tb[2]+cb),min(ea,tb[3]+cb),cb,min(ea,sum(tb[2:])+cb)]
        if any(abs(x)>y for x,y in zip(r,budgets)):raise ValueError('complete endpoint full split physical energy gate failed')
        totals=[x+y for x,y in zip(totals,r)];global_budgets=[x+y for x,y in zip(global_budgets,budgets)]
        cells.append(dict(valid=True,residuals=list(map(_display,r)),budgets=list(map(_display,budgets))))
    global_budgets=[min(pa if k<2 else ea,x) for k,x in enumerate(global_budgets)]
    valid=transport['valid'] and all(abs(x)<=y for x,y in zip(totals,global_budgets))
    return dict(valid=valid,transport=transport,collisions=children,cells=cells,whole_interval_particle_energy_closed=valid,
        row_order=['electron_particles','hole_particles','electron_energy','hole_energy','lattice_energy','total_energy'],
        global_residuals=list(map(_display,totals)),global_budgets=list(map(_display,global_budgets)),outward_contact_transfers=list(map(_display,boundary)),
        physical_clock_advanced_once=True,auxiliary_clock_projection_checked=True,source_and_contact_ownership_checked=True,
        native_physics_used=False,complete_device_energy=False,physical_validated=False)

def audit_mb_weak_conducting_split(configurations,old,new,report,*,faces,thermal_faces,dt_s,impulses_J=None,energy_atol_J=1e-27):
    old=tuple(map(saved_state,old));new=tuple(map(saved_state,new));n=len(old);ea=min(_command(energy_atol_J),Fraction(1,10**27));dt=_binary113(_command(dt_s))
    if len(new)!=n or not n or ea<=0 or dt<=0:raise ValueError('conducting split coverage/budget')
    middle=tuple(map(saved_state,report['pre_lattice_states']));base=report['carrier_split']
    _metadata(report,dict(scope='weak_endpoint_transport_collision_Fourier_Lie_split',execution_backend='native',precision_bits=113,temporal_order=1,autonomous_operators_only=True,monolithic_coupled_BE=False,dt_s=float(dt_s),old_sha256=list(map(_saved_fingerprint,old)),new_sha256=list(map(_saved_fingerprint,new)),physical_time_advanced=True,lattice_flux_included=True,field_work_included=False,complete_device_energy=False,physical_validated=False))
    checked=audit_mb_weak_endpoint_split(configurations,old,middle,base,faces=faces,dt_s=dt_s,impulses_J=impulses_J,energy_atol_J=energy_atol_J/2)
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

def audit_mb_weak_rounded_split(configurations,old,new,report,*,faces,thermal_faces,dt_s,
                                    impulses_J=None,particle_atol=1e-9,energy_atol_J=1e-27):
    old=tuple(map(saved_state,old));new=tuple(map(saved_state,new));n=len(old)
    pa=min(_command(particle_atol),Fraction(1,10**9));ea=min(_command(energy_atol_J),Fraction(1,10**27))
    if min(pa,ea,_command(dt_s))<=0 or len(new)!=n or not 1<=n<=256:
        raise ValueError('rounded split coverage/budget')
    _metadata(report,dict(scope='accounted_weak_RN113_transport_collision_Fourier_Lie_split',
        execution_backend='native',precision_bits=113,temporal_order=1,dt_s=float(dt_s),
        old_sha256=list(map(_saved_fingerprint,old)),new_sha256=list(map(_saved_fingerprint,new)),
        exact_recurrence_preserved=False,rounding_error_included=True,physical_time_advanced=True,
        lattice_flux_included=True,field_work_included=False,complete_device_energy=False,physical_validated=False))
    rounded=tuple(map(saved_state,report['rounded_states']))
    rounding,rb=_rounding(old,rounded,report['rounding'],particle_atol,energy_atol_J/2)
    child=report['conducting'];base=child['carrier_split'];dt=_binary113(_command(dt_s))
    checked=audit_mb_weak_conducting_split(configurations,rounded,new,child,
        faces=faces,thermal_faces=thermal_faces,dt_s=dt_s,impulses_J=impulses_J,energy_atol_J=energy_atol_J/2)
    heat,signed_heat,hb=_stage(child['pre_lattice_states'],new,child['lattice'],thermal_faces,dt_s,energy_atol_J/4)
    signed=[[Fraction()]*4 for s in old];scales=[[Fraction()]*4 for s in old]
    for spec,row in zip(faces,base['transport']['transfers']):
        values,packets,j=_values(moment_wire(row['raw']),'mb_scaled_moments_v1',4)
        for k,x in enumerate(values):
            value=_multiply(x,dt);i=spec['owner'];signed[i][k]-=value;scales[i][k]+=abs(value)
            if 'neighbor' in spec:signed[spec['neighbor']][k]+=value;scales[spec['neighbor']][k]+=abs(value)
    impulses=[(0.,0.,0.) for s in old] if impulses_J is None else impulses_J
    totals=[Fraction()]*6;budgets=[Fraction()]*6;cells=[]
    for i,(a,b) in enumerate(zip(old,new)):
        before=point(a.endpoint);after=point(b.endpoint);f=before['frame'];V=f[4]
        dN=[V*(after['n'][k]-before['n'][k]) for k in (0,1)]
        dU=[V*(after['K'][k]-before['K'][k]+f[5+k]*(after['n'][k]-before['n'][k])) for k in (0,1)]
        dL=V*f[3]*(after['Tl']-before['Tl']);imp=list(map(_command,impulses[i]))
        mid=base['transported_states'][i];c=base['collisions'][i]
        exchange,cb=exchange_budget(mid['endpoint'],c['command'],c['root_packet'])
        r=[dN[k]-signed[i][k] for k in (0,1)]+[dU[k]-signed[i][2+k]+exchange[k]-imp[k] for k in (0,1)]
        r.extend((dL-sum(exchange)-imp[2]-signed_heat[i],sum(dU)+dL-sum(signed[i][2:])-sum(imp)-signed_heat[i]))
        tb=[min(pa if k<2 else _command(energy_atol_J/8),4096*EPS*x) for k,x in enumerate(scales[i])]
        b0=[*tb[:2],tb[2]+cb+hb[i],tb[3]+cb+hb[i],cb+hb[i],sum(tb[2:])+cb+hb[i]]
        budget=[min(pa if k<2 else ea,x+y) for k,(x,y) in enumerate(zip(b0,rb[i]))]
        if any(abs(x)>y for x,y in zip(r,budget)):raise ValueError('rounded split actual full-interval energy gate failed')
        totals=[x+y for x,y in zip(totals,r)];budgets=[x+y for x,y in zip(budgets,budget)]
        cells.append(dict(valid=True,residuals=list(map(_display,r)),budgets=list(map(_display,budget))))
    budgets=[min(pa if k<2 else ea,x) for k,x in enumerate(budgets)]
    if any(abs(x)>y for x,y in zip(totals,budgets)):raise ValueError('rounded split global energy gate failed')
    return dict(valid=True,rounding=rounding,conducting=checked,cells=cells,
        global_residuals=list(map(_display,totals)),global_budgets=list(map(_display,budgets)),
        whole_interval_particle_energy_closed_with_rounding_budget=True,physical_clock_advanced_once=True,
        rounding_error_included=True,exact_recurrence_preserved=False,native_physics_used=False,
        complete_device_energy=False,physical_validated=False)

