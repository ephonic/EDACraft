"""Independent complete-endpoint collision and single-interval split audits."""
from dataclasses import asdict
from fractions import Fraction
import hashlib,json
from .boltzmann_scaled_split import ALPHA,EPS,_command,_display,_metadata,_saved_fingerprint
from .boltzmann_recomputed_transport import (
    point,_decode,_wire,scaled_value_fraction,saved_state,audit_mb_scaled_transport,
    moment_wire,_values,
)
from .boltzmann_recomputed_endpoint_collision import _expected
from .boltzmann_weak_endpoint_powerlaw import audit_mb_weak_endpoint_powerlaw,split_mb_weak_endpoint_powerlaw,scaled_powerlaw_aggregates
from .boltzmann_product_range import _vector,_binary113


def configuration(raw):
    if not isinstance(raw,dict):raw=asdict(raw)
    if set(raw)!={'parameters','valleys_n','valleys_p'}:raise ValueError('complete endpoint configuration coverage')
    if len(raw['parameters'])!=14:raise ValueError('complete endpoint parameter coverage')
    sha=hashlib.sha256(json.dumps(tuple(raw[k] for k in ('parameters','valleys_n','valleys_p')),separators=(',',':')).encode()).hexdigest()
    return raw,sha


def exchange_budget(endpoint,command,packet):
    parts=split_mb_weak_endpoint_powerlaw(packet)
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


def audit_mb_weak_endpoint_collision(cfg,old,new,report,*,dt_s,impulses_J=(0.,0.,0.),energy_atol_J=1e-27):
    a,b=map(saved_state,(old,new));dt,ea=map(_command,(dt_s,energy_atol_J));q=list(map(_command,impulses_J))
    if dt<=0 or ea<=0 or len(q)!=3:raise ValueError('positive endpoint collision duration/budget and three impulses required')
    cfg,digest=configuration(cfg);p=point(a.endpoint);f=p['frame'];command=report['command'];c=_vector(command)
    if len(c)!=18 or c[:14]!=_vector(cfg['parameters']) or c[14:]!=list(map(_binary113,(dt,*q))):
        raise ValueError('endpoint collision external configuration/duration/source mismatch')
    _metadata(report,dict(scope='weak_complete_endpoint_powerlaw_collision',execution_backend='native',precision_bits=113,
        configuration_sha256=digest,old_sha256=_saved_fingerprint(a),new_sha256=_saved_fingerprint(b),dt_s=float(dt_s),
        physical_time_advanced=True,complete_device_energy=False,physical_validated=False))
    packet=report['root_packet'];check=audit_mb_weak_endpoint_powerlaw(a.endpoint,command,a.physical_clock,packet)
    parts=split_mb_weak_endpoint_powerlaw(packet);aggregates=scaled_powerlaw_aggregates(parts['proof'])
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

