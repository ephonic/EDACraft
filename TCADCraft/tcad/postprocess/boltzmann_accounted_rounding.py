"""Independent RN113 endpoint perturbation and complete-interval accounting.

This is an explicit approximate algorithm, separate from the exact recurrence.
Every coordinate difference is retained. Only stdlib/postprocess code is used.
"""
from fractions import Fraction
from .boltzmann_recomputed_transport import (
    _decode, _take, _wire, point, saved_state, scaled_value_fraction, moment_wire, _values,
)
from .boltzmann_scaled_arithmetic import _tokens, _count
from .boltzmann_scaled_split import ALPHA, EPS, _command, _display, _metadata, _saved_fingerprint
from .boltzmann_product_range import _binary113
from .boltzmann_scaled_collision_trace import _multiply
from .boltzmann_recomputed_endpoint_split import exchange_budget
from .boltzmann_recomputed_lattice_transport import audit_mb_recomputed_conducting_endpoint_split, _stage


def split_rounding(raw):
    _tokens(raw,60000)
    if len(raw)<4 or tuple(raw[:2])!=('mb_accounted_rounding_v1','113'):
        raise ValueError('accounted rounding version/precision')
    count=_count(raw[2],4096);endpoint,j=_take(raw,3,60000)
    frame,values=_decode(endpoint);tails=[]
    for k in range(7):
        packet,j=_take(raw,j);x=scaled_value_fraction(packet)
        if _wire(x)!=packet:raise ValueError('rounding difference noncanonical')
        tails.append(x)
    if j!=len(raw) or sum(int(_wire(x)[2]) for x in values+tails)!=count:
        raise ValueError('rounding combined saved coverage/budget')
    return endpoint,values,tails


def _rounding_cell(old,new,raw):
    a,b=map(saved_state,(old,new));p=point(a.endpoint);q=point(b.endpoint)
    frame,v=_decode(a.endpoint);other,w=_decode(b.endpoint);endpoint,values,tails=split_rounding(raw)
    if list(b.endpoint)!=endpoint or frame!=other or w!=list(map(_binary113,v)):
        raise ValueError('rounding endpoint/frame/RN113 mismatch')
    if any(x!=y+z for x,y,z in zip(v,w,tails)):
        raise ValueError('rounding exact coordinate difference mismatch')
    if a.time_s!=b.time_s or a.physical_clock!=b.physical_clock:
        raise ValueError('rounding must preserve physical clock')
    V=frame[4];dv=[y-x for x,y in zip(v,w)];bounds=[EPS*abs(x) for x in v]
    if any(abs(x)>y for x,y in zip(dv,bounds)):
        raise ValueError('rounding coordinate error bound')
    # Actual physical coordinates, not the saved claimed residuals.
    dN=[V*(q['n'][k]-p['n'][k]) for k in (0,1)]
    dU=[V*(q['K'][k]-p['K'][k]+frame[5+k]*(q['n'][k]-p['n'][k])) for k in (0,1)]
    dL=V*frame[3]*(q['Tl']-p['Tl'])
    r=[*dN,*dU,dL,sum(dU)+dL]
    u=[V*(ALPHA*frame[k]*bounds[0]/frame[3]+bounds[1+k]+bounds[5+k]) for k in (0,1)]
    budget=[V*bounds[3],V*bounds[4],*u,V*bounds[0],sum(u)+V*bounds[0]]
    if any(abs(x)>y for x,y in zip(r,budget)):
        raise ValueError('rounding actual particle/energy bound')
    return dict(valid=True,coordinate_differences_exactly_saved=True,
                physical_clock_preserved=True,residuals=list(map(_display,r)),
                budgets=list(map(_display,budget))),r,budget


def _rounding(old,new,report,particle_atol,energy_atol_J):
    old=tuple(map(saved_state,old));new=tuple(map(saved_state,new));n=len(old)
    pa=min(_command(particle_atol),Fraction(1,10**9));ea=min(_command(energy_atol_J),Fraction(1,10**27))
    if not 1<=n<=256 or len(new)!=n or min(pa,ea)<=0:
        raise ValueError('bounded rounding coverage and positive budget required')
    _metadata(report,dict(scope='explicit_accounted_RN113_endpoint_rounding',execution_backend='native',
                         precision_bits=113,old_sha256=list(map(_saved_fingerprint,old)),
                         new_sha256=list(map(_saved_fingerprint,new)),physical_time_advanced=False,
                         exact_recurrence_preserved=False,coordinate_differences_exactly_saved=True,
                         complete_device_energy=False,physical_validated=False))
    if len(report['cells'])!=n:raise ValueError('rounding cell coverage')
    if any(s.time_s!=old[0].time_s or s.physical_clock!=old[0].physical_clock for s in old):
        raise ValueError('rounding requires synchronized clocks')
    totals=[Fraction()]*6;budgets=[Fraction()]*6;checks=[];exact=[]
    for a,b,raw in zip(old,new,report['cells']):
        c,r,t=_rounding_cell(a,b,raw);checks.append(c);exact.append(t)
        if any(x>(pa if k<2 else ea)/n for k,x in enumerate(t)):
            raise ValueError('rounding perturbation budget exceeds hard allowance')
        totals=[x+y for x,y in zip(totals,r)];budgets=[x+y for x,y in zip(budgets,t)]
    check=dict(valid=True,cells=checks,global_residuals=list(map(_display,totals)),
               global_budgets=list(map(_display,budgets)),coordinate_differences_exactly_saved=True,
               physical_clock_preserved=True,exact_recurrence_preserved=False,
               native_physics_used=False,complete_device_energy=False,physical_validated=False)
    return check,exact


def audit_mb_accounted_rounding(old,new,report,*,particle_atol=1e-9,energy_atol_J=1e-27):
    return _rounding(old,new,report,particle_atol,energy_atol_J)[0]


def audit_mb_rounded_conducting_split(configurations,old,new,report,*,faces,thermal_faces,dt_s,
                                    impulses_J=None,particle_atol=1e-9,energy_atol_J=1e-27):
    old=tuple(map(saved_state,old));new=tuple(map(saved_state,new));n=len(old)
    pa=min(_command(particle_atol),Fraction(1,10**9));ea=min(_command(energy_atol_J),Fraction(1,10**27))
    if min(pa,ea,_command(dt_s))<=0 or len(new)!=n or not 1<=n<=256:
        raise ValueError('rounded split coverage/budget')
    _metadata(report,dict(scope='accounted_RN113_transport_collision_Fourier_Lie_split',
        execution_backend='native',precision_bits=113,temporal_order=1,dt_s=float(dt_s),
        old_sha256=list(map(_saved_fingerprint,old)),new_sha256=list(map(_saved_fingerprint,new)),
        exact_recurrence_preserved=False,rounding_error_included=True,physical_time_advanced=True,
        lattice_flux_included=True,field_work_included=False,complete_device_energy=False,physical_validated=False))
    rounded=tuple(map(saved_state,report['rounded_states']))
    rounding,rb=_rounding(old,rounded,report['rounding'],particle_atol,energy_atol_J/2)
    child=report['conducting'];base=child['carrier_split'];dt=_binary113(_command(dt_s))
    checked=audit_mb_recomputed_conducting_endpoint_split(configurations,rounded,new,child,
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
