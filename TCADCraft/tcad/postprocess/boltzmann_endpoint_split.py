"""Independent complete-endpoint collision and single-interval split audits."""
from dataclasses import asdict
from fractions import Fraction
import hashlib,json
from .boltzmann_scaled_split import ALPHA,EPS,_command,_display,_metadata,_saved_fingerprint
from .boltzmann_scaled_transport import (
    point,_decode,_wire,scaled_value_fraction,saved_state,audit_mb_scaled_transport,
    moment_wire,_values,
)
from .boltzmann_endpoint_collision import _expected
from .boltzmann_endpoint_powerlaw import audit_mb_endpoint_powerlaw,split_mb_endpoint_powerlaw,scaled_powerlaw_aggregates
from .boltzmann_product_range import _vector,_binary113


def configuration(raw):
    if not isinstance(raw,dict):raw=asdict(raw)
    if set(raw)!={'parameters','valleys_n','valleys_p'}:raise ValueError('complete endpoint configuration coverage')
    if len(raw['parameters'])!=14:raise ValueError('complete endpoint parameter coverage')
    sha=hashlib.sha256(json.dumps(tuple(raw[k] for k in ('parameters','valleys_n','valleys_p')),separators=(',',':')).encode()).hexdigest()
    return raw,sha


def exchange_budget(endpoint,command,packet):
    parts=split_mb_endpoint_powerlaw(packet)
    fixed=[command[14],*parts['chosen'][1:],*command[15:]]
    v={label:q for label,q,r in _expected(endpoint,fixed)}
    groups=[label[:-6] for label in v if label.startswith('lineage') and label.endswith('.input')]
    a=point(endpoint);f=a['frame'];density=a['n'];budget=Fraction()
    sources=[False for k in (0,1) if v['delta'+str(k)]]+[True for k in range(3) if v['source'+str(k)]]
    for g,source in zip(groups,sources):
        X=[v[g+'.'+str(j)] for j in (10,11)];L=v[g+'.12']
        scale=f[4]*(sum(map(abs,X))+abs(L)*(1+ALPHA*sum(map(abs,density))/f[3])+(abs(v[g+'.input']) if source else 0))
        budget+=min(Fraction(1,10**27)/max(1,len(groups)),4096*EPS*scale)
    exchange=[f[4]*sum((v[g+'.'+str(j)] for g in groups),Fraction()) for j in (10,11)]
    return exchange,min(Fraction(1,10**27),budget)


def audit_mb_endpoint_collision(cfg,old,new,report,*,dt_s,impulses_J=(0.,0.,0.),energy_atol_J=1e-27):
    a,b=map(saved_state,(old,new));dt,ea=map(_command,(dt_s,energy_atol_J));q=list(map(_command,impulses_J))
    if dt<=0 or ea<=0 or len(q)!=3:raise ValueError('positive endpoint collision duration/budget and three impulses required')
    cfg,digest=configuration(cfg);p=point(a.endpoint);f=p['frame'];command=report['command'];c=_vector(command)
    if len(c)!=18 or c[:14]!=_vector(cfg['parameters']) or c[14:]!=list(map(_binary113,(dt,*q))):
        raise ValueError('endpoint collision external configuration/duration/source mismatch')
    _metadata(report,dict(scope='complete_endpoint_powerlaw_collision',execution_backend='native',precision_bits=113,
        configuration_sha256=digest,old_sha256=_saved_fingerprint(a),new_sha256=_saved_fingerprint(b),dt_s=float(dt_s),
        physical_time_advanced=True,complete_device_energy=False,physical_validated=False))
    packet=report['root_packet'];check=audit_mb_endpoint_powerlaw(a.endpoint,command,a.physical_clock,packet)
    parts=split_mb_endpoint_powerlaw(packet);aggregates=scaled_powerlaw_aggregates(parts['proof'])
    inc=[scaled_value_fraction(aggregates['aggregate.'+k]) for k in ('L','un','up')]
    g,v=_decode(a.endpoint);h,w=_decode(b.endpoint);expected=v.copy()
    for k,x in zip((0,5,6),inc):expected[k]+=x
    end=scaled_value_fraction(a.physical_clock)+_binary113(dt)
    if h!=g or w!=expected:raise ValueError('complete endpoint collision lost source coordinates or increments')
    if list(b.physical_clock)!=parts['end'] or list(b.physical_clock)!=_wire(end) or b.time_s!=float(end):
        raise ValueError('complete endpoint collision exact clock mismatch')
    after=point(b.endpoint);V=f[4];exchange,budget=exchange_budget(a.endpoint,command,packet)
    if budget>ea:raise ValueError('complete endpoint collision exceeds supplied energy cap')
    dU=[V*(after['K'][k]-p['K'][k]) for k in (0,1)];dL=V*f[3]*(after['Tl']-p['Tl'])
    residual=[V*(after['n'][k]-p['n'][k]) for k in (0,1)]+[dU[k]+exchange[k]-q[k] for k in (0,1)]+[dL-sum(exchange)-q[2],sum(dU)+dL-sum(q)]
    budgets=[Fraction(),Fraction(),budget,budget,budget,budget]
    if any(abs(x)>y for x,y in zip(residual,budgets)):raise ValueError('complete endpoint actual collision energy closure failed')
    return dict(valid=True,root=check,actual_endpoint_graph_checked=True,exact_clock_advanced_once=True,
        residuals=list(map(_display,residual)),budgets=list(map(_display,budgets)),exchange_J=list(map(_display,exchange)),
        native_physics_used=False,complete_device_energy=False,physical_validated=False)


def audit_mb_endpoint_split(configurations,old,new,report,*,faces,dt_s,impulses_J=None,
                            particle_atol=1e-9,energy_atol_J=1e-27,number_atol_s=1e-6,energy_atol_W=1e-15):
    old=tuple(map(saved_state,old));new=tuple(map(saved_state,new));n=len(old)
    dt,pa,ea=map(_command,(dt_s,particle_atol,energy_atol_J))
    if min(dt,pa,ea)<=0 or not 1<=n<=256 or len(new)!=n or len(configurations)!=n:raise ValueError('complete endpoint split coverage/budget')
    cfg=[configuration(c) for c in configurations];q=[(0.,0.,0.) for s in old] if impulses_J is None else impulses_J
    if len(q)!=n or any(len(row)!=3 for row in q):raise ValueError('complete endpoint split impulse coverage')
    impulses=[list(map(_command,row)) for row in q]
    _metadata(report,dict(scope='complete_endpoint_same_interval_Lie_split',execution_backend='native',precision_bits=113,
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
        checked=audit_mb_endpoint_collision(config,mid,child,report['collisions'][i],dt_s=dt_s,impulses_J=q[i],energy_atol_J=energy_atol_J/(2*n));children.append(checked)
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
