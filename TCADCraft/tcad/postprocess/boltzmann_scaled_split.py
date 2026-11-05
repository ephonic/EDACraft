"""Independent saved scaled split audit. Only stdlib and postprocessors are used."""
from dataclasses import asdict
from decimal import Decimal, localcontext
from fractions import Fraction
import math
import hashlib, json

from .boltzmann_affine_transport import _fingerprint, _metadata
from .boltzmann_split_interval import _load
from .boltzmann_nonisothermal_transport import audit_mb_nonisothermal_transport
from .boltzmann_product_range import _vector, _binary113
from .boltzmann_scaled_collision_tail import _endpoint
from .boltzmann_scaled_arithmetic import scaled_value_fraction
from .boltzmann_scaled_collision_trace import _expected, _wire
from .boltzmann_scaled_powerlaw import (
    audit_mb_scaled_powerlaw, split_mb_scaled_powerlaw, scaled_powerlaw_aggregates,
)

ALPHA=Fraction(3,2)*Fraction(Decimal('1.380649e-23'))
EPS=Fraction(1,1 << 112)
CANDIDATE_FIELDS={'source_endpoint','command','source_clock','lattice_increment',
    'electron_energy_increment','hole_energy_increment','start_clock','end_clock','root_packet'}


def _saved_fingerprint(state):
    raw=state if isinstance(state,dict) else asdict(state)
    return hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _encode(state):
    anchor=state.anchor if hasattr(state,'anchor') else state
    changes=[getattr(state,k,()) for k in ('electron_density_change','hole_density_change',
                                           'electron_energy_density_change','hole_energy_density_change')]
    return [s for g in (anchor.frame,anchor.electron_excess,anchor.hole_excess,*changes) for s in (str(len(g)),*g)]


def _command(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('finite independent scaled split command required')
    return Fraction(value)


def _clock(value):
    return _wire(_binary113(_command(value)))


def _display(x):
    with localcontext() as ctx:
        ctx.prec=40
        return format(Decimal(x.numerator)/Decimal(x.denominator),'.12E')


def _point(endpoint,increments=(0,0,0)):
    f,en,ep,dn,dp,un,up=_endpoint(endpoint)
    L,du,dv=increments
    Tl=f[2]+(sum(f[9:],Fraction())+L)/f[3]
    n=[f[k]+sum((dn,dp)[k],Fraction()) for k in range(2)]
    K=[ALPHA*Tl*f[k]+sum((en,ep)[k]+(un,up)[k],Fraction())+(du,dv)[k]-f[5+k]*sum((dn,dp)[k],Fraction()) for k in range(2)]
    return dict(frame=f,Tl=Tl,n=n,K=K,temperatures=[Tl,*[K[k]/(ALPHA*n[k]) for k in range(2)]])


def audit_mb_scaled_state(state):
    """Audit a saved projected state without invoking production constructors."""
    raw=asdict(state) if not isinstance(state,dict) else state
    if set(raw)!={'collision','time_s','physical_clock'}:raise ValueError('scaled submitted state coverage')
    c=raw['collision']
    if not isinstance(c,dict) or set(c)!=CANDIDATE_FIELDS:raise ValueError('scaled collision state coverage')
    parts=split_mb_scaled_powerlaw(c['root_packet']);values=scaled_powerlaw_aggregates(parts['proof'])
    for key,label in (('lattice_increment','L'),('electron_energy_increment','un'),('hole_energy_increment','up')):
        if list(c[key])!=values['aggregate.'+label]:raise ValueError('scaled submitted increment detached from proof')
    if list(c['start_clock'])!=parts['start'] or list(c['end_clock'])!=parts['end']:
        raise ValueError('scaled submitted auxiliary clock detached from proof')
    if list(raw['physical_clock'])!=parts['start'] or list(raw['physical_clock'])!=_clock(raw['time_s']):
        raise ValueError('scaled submitted physical clock projection mismatch')
    check=audit_mb_scaled_powerlaw(c['source_endpoint'],c['command'],c['source_clock'],c['root_packet'])
    point=_point(c['source_endpoint'],tuple(scaled_value_fraction(values['aggregate.'+k]) for k in ('L','un','up')))
    return dict(valid=check['valid'],collision=check,temperatures_K=list(map(_display,point['temperatures'])),
                scaled_components_preserved=True,physical_clock_projection_checked=True,physical_validated=False)


def _exchanges_and_budget(c):
    parts=split_mb_scaled_powerlaw(c['root_packet'])
    command=[c['command'][14],*parts['chosen'][1:],*c['command'][15:]]
    values={label:q for label,q,r in _expected(c['source_endpoint'],command)}
    f=_endpoint(c['source_endpoint'])[0];groups=[label[:-6] for label in values if label.startswith('lineage') and label.endswith('.input')]
    exchange=[f[4]*sum((values[g+'.'+str(j)] for g in groups),Fraction()) for j in (10,11)]
    density=_point(c['source_endpoint'])['n']
    kinds=[False for k in (0,1) if values['delta'+str(k)]]+[True for k in range(3) if values['source'+str(k)]]
    budgets=[]
    for g,source in zip(groups,kinds):
        X=[values[g+'.'+str(j)] for j in (10,11)];L=values[g+'.12']
        scale=f[4]*(sum(map(abs,X))+abs(L)*(1+ALPHA*sum(map(abs,density))/f[3])+(abs(values[g+'.input']) if source else 0))
        budgets.append(min(Fraction(1,10**27)/max(1,len(groups)),4096*EPS*scale))
    return exchange,min(Fraction(1,10**27),sum(budgets,Fraction()))


def audit_mb_scaled_split_interval(configurations,old,new,report,*,faces,dt_s,impulses_J=None,
                                    particle_atol=1e-9,energy_atol_J=1e-27,number_atol_s=1e-6,energy_atol_W=1e-15):
    dt,pa,ea,nfa,efa=map(_command,(dt_s,particle_atol,energy_atol_J,number_atol_s,energy_atol_W));n=len(old)
    if min(dt,pa,ea,nfa,efa)<=0 or not 1<=n<=256 or len(new)!=n or len(configurations)!=n:
        raise ValueError('scaled split independent coverage/budget mismatch')
    start=old[0].time_s;end=start+float(dt_s)
    if not math.isfinite(end) or not start<end or any(s.time_s!=start for s in old):
        raise ValueError('scaled split synchronized physical clock required')
    _metadata(report,dict(scope='scaled_same_interval_Lie_split_flat_MB',execution_backend='native',precision_bits=113,
        method='transport_explicit_then_collision_BE',temporal_order=1,autonomous_operators_only=True,
        stage_clock_model='exact_scaled_auxiliary_then_project',dt_s=float(dt_s),physical_time_advanced=True,
        production_binding_integrated=True,state_commit_integrated=True,repeat_scaled_transport_supported=False,
        monolithic_coupled_BE=False,field_work_included=False,lattice_flux_included=False,
        complete_device_energy=False,physical_validated=False))
    if report['physical_interval_s']!=[start,end] or report['configuration_sha256']!=[c.sha256 for c in configurations] or report['old_sha256']!=list(map(_fingerprint,old)) or report['new_sha256']!=list(map(_saved_fingerprint,new)):
        raise ValueError('scaled split state/interval provenance mismatch')
    q=[(0.,0.,0.) for s in old] if impulses_J is None else impulses_J
    if len(q)!=n or any(len(row)!=3 for row in q):raise ValueError('scaled split impulse coverage')
    qd=[list(map(_command,row)) for row in q]
    saved=report['transported_states']
    if len(saved)!=n:raise ValueError('scaled split transport state coverage')
    middle=tuple(map(_load,saved))
    transport=audit_mb_nonisothermal_transport(old,middle,report['transport'],faces=faces,dt_s=dt_s,
        particle_atol=particle_atol,energy_atol_J=energy_atol_J/2,number_atol_s=number_atol_s,energy_atol_W=energy_atol_W)
    signed=[[Fraction() for k in range(4)] for s in old];scales=[[Fraction() for k in range(4)] for s in old];boundary=[Fraction()]*4
    for spec,row in zip(faces,report['transport']['transfers']):
        for k,raw in enumerate(row['integrated']):
            vals=_vector(raw);value=sum(vals,Fraction());scale=sum(map(abs,vals),Fraction());i=spec['owner']
            signed[i][k]-=value;scales[i][k]+=scale
            if 'reservoir' in spec:boundary[k]+=value
            else:signed[spec['neighbor']][k]+=value;scales[spec['neighbor']][k]+=scale
    cells=[];children=[];residuals=[Fraction()]*6;budgets=[Fraction()]*6;valid=transport['valid']
    for i,(cfg,a,b,mid) in enumerate(zip(configurations,old,new,middle)):
        raw=asdict(b) if not isinstance(b,dict) else b;c=raw['collision']
        if raw['time_s']!=end or list(c['source_endpoint'])!=_encode(mid):raise ValueError('scaled split submitted source/clock mismatch')
        command=_vector(c['command']);expected_config=_vector(cfg.parameters)
        if command[:14]!=expected_config or command[14:]!=[_binary113(x) for x in (dt,*qd[i])]:
            raise ValueError('scaled split external configuration/duration/source mismatch')
        if _vector(c['source_clock'])!=[_binary113(_command(end))]:raise ValueError('scaled split auxiliary start mismatch')
        check=audit_mb_scaled_state(raw);children.append(check);valid &= check['valid']
        after=_point(c['source_endpoint'],tuple(scaled_value_fraction(c[k]) for k in ('lattice_increment','electron_energy_increment','hole_energy_increment')))
        before=_point(_encode(a));f=before['frame'];V=f[4]
        dN=[V*(after['n'][k]-before['n'][k]) for k in (0,1)]
        dU=[V*(after['K'][k]-before['K'][k]+f[k+5]*(after['n'][k]-before['n'][k])) for k in (0,1)]
        dU.append(V*f[3]*(after['Tl']-before['Tl']))
        exchange,cb=_exchanges_and_budget(c)
        if cb>ea/(2*n):raise ValueError('scaled collision exceeds allocated split energy budget')
        r=[dN[k]-signed[i][k] for k in (0,1)]+[dU[k]-signed[i][k+2]+exchange[k]-qd[i][k] for k in (0,1)]
        r.extend((dU[2]-sum(exchange)-qd[i][2],sum(dU)-sum(signed[i][2:])-sum(qd[i])))
        tb=[min(pa if k<2 else _command(energy_atol_J/2),4096*EPS*v) for k,v in enumerate(scales[i])]
        budget=[*tb[:2],min(ea,tb[2]+cb),min(ea,tb[3]+cb),min(ea,cb),min(ea,tb[2]+tb[3]+cb)]
        passed=all(abs(x)<=y for x,y in zip(r,budget));valid &= passed
        residuals=[x+y for x,y in zip(residuals,r)];budgets=[x+y for x,y in zip(budgets,budget)]
        cells.append(dict(valid=passed,residuals=list(map(_display,r)),budgets=list(map(_display,budget))))
    budgets=[min(pa if k<2 else ea,v) for k,v in enumerate(budgets)]
    closed=all(abs(x)<=y for x,y in zip(residuals,budgets));valid &= closed
    return dict(valid=bool(valid),transport=transport,collisions=children,cells=cells,
        row_order=['electron_particles','hole_particles','electron_energy','hole_energy','lattice_energy','total_energy'],
        global_residuals=list(map(_display,residuals)),global_budgets=list(map(_display,budgets)),outward_contact_transfers=list(map(_display,boundary)),
        whole_interval_particle_energy_closed=closed,physical_clock_advanced_once=True,auxiliary_clock_projection_checked=True,
        source_and_contact_ownership_checked=True,native_physics_used=False,repeat_scaled_transport_supported=False,
        complete_device_energy=False,physical_validated=False)
