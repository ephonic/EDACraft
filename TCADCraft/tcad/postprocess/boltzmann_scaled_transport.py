"""Saved full-density scaled MB transport replay; stdlib only."""
from dataclasses import asdict,dataclass
from decimal import Decimal
from fractions import Fraction
from functools import lru_cache
import math
from .boltzmann_scaled_arithmetic import _tokens,_count,scaled_value_fraction
from .boltzmann_scaled_collision_trace import _wire,_atoms,_divide,_multiply
from .boltzmann_scaled_collision_tail import _endpoint
from .boltzmann_product_range import _vector,_binary113
from .boltzmann_scaled_split import ALPHA,EPS,_command,_display,_clock,_saved_fingerprint,_metadata


@lru_cache(maxsize=64)
def _quotient(a,b):
    """Cache only independent arithmetic, keyed by the complete exact operands.

    Atoms are always the canonical fixed113 partition. Proof comparisons and
    physical checks still run for each submitted packet. No producer value is
    cached. Fraction keys/results are immutable; at most 64 entries are kept.
    """
    return _divide(_atoms(a),b)


def _take(raw,j,maximum=8195):
    if j>=len(raw):raise ValueError('missing scaled transport packet')
    n=_count(raw[j],maximum);p=list(raw[j+1:j+1+n])
    if len(p)!=n:raise ValueError('truncated scaled transport packet')
    return p,j+1+n


def _decode(raw):
    _tokens(raw,60000)
    if len(raw)<12 or tuple(raw[:3])!=('mb_scaled_endpoint_v1','113','9'):raise ValueError('scaled endpoint framing')
    f=_vector(raw[3:12]);v=[];j=12;evidence=0
    for k in range(7):
        packet,j=_take(raw,j);x=scaled_value_fraction(packet)
        if _wire(x)!=packet:raise ValueError('noncanonical scaled endpoint partition')
        v.append(x);evidence+=int(packet[2])
    if j!=len(raw) or evidence>4096:raise ValueError('scaled endpoint coverage/budget')
    if any(not Fraction(1,10**1000)<=f[k]<=10**1000 for k in (0,1,3,4)) or max(abs(f[5]),abs(f[6]))>10**1000:
        raise ValueError('scaled endpoint reference/band range')
    if not 1<f[2]<100000 or not 1<f[7]<f[8]<100000:raise ValueError('scaled endpoint temperature domain')
    return f,v


def endpoint_wire(frame,values):
    result=['mb_scaled_endpoint_v1','113','9',*frame]
    for v in values:
        wire=_wire(v);result.extend((str(len(wire)),*wire))
    _decode(result);return result


def point(raw):
    f,v=_decode(raw);Tl=f[2]+v[0]/f[3];n=[f[k]+v[3+k] for k in (0,1)]
    if any(not Fraction(1,10**1000)<=x<=10**1000 for x in n):raise ValueError('scaled actual density outside domain')
    K=[ALPHA*Tl*f[k]+v[1+k]+v[5+k]-f[5+k]*v[3+k] for k in (0,1)]
    temperatures=[Tl,*[K[k]/(ALPHA*n[k]) for k in (0,1)]];env=128*EPS*max(1,*map(abs,temperatures))
    if any(T<f[7]-env or T>f[8]+env for T in temperatures):raise ValueError('scaled actual temperature outside domain')
    return dict(frame=f,values=v,Tl=Tl,n=n,K=K,temperatures=temperatures)


def audit_scaled_endpoint_import(original,increments,raw):
    f,en,ep,dn,dp,un,up=_endpoint(original);g,v=_decode(raw)
    L,du,dv=map(scaled_value_fraction,increments)
    expected=[sum(f[9:],Fraction())+L,sum(en,Fraction()),sum(ep,Fraction()),sum(dn,Fraction()),sum(dp,Fraction()),sum(un,Fraction())+du,sum(up,Fraction())+dv]
    if g!=f[:9] or v!=expected:raise ValueError('scaled materialization lost or changed source components')
    p=point(raw)
    return dict(valid=True,exact_materialization=True,temperatures_K=list(map(_display,p['temperatures'])),physical_time_advanced=False,physical_validated=False)


def _values(raw,name,n,j=3):
    if tuple(raw[:3])!=(name,'113',str(n)):raise ValueError('scaled transport value framing')
    result=[];packets=[]
    for k in range(n):
        p,j=_take(raw,j);x=scaled_value_fraction(p)
        if p!=_wire(x):raise ValueError('scaled transport value partition')
        result.append(x);packets.append(p)
    return result,packets,j


def face_values(raw):
    _tokens(raw,65535)
    values,packets,j=_values(raw,'mb_scaled_face_v1',10,8)
    if j!=len(raw) or 5+sum(int(p[2]) for p in packets)>4096:raise ValueError('scaled face evidence/trailing data')
    return _vector(raw[3:8]),values,packets


def moment_wire(raw):
    coeff,v,packets=face_values(raw)
    return ['mb_scaled_moments_v1','113','4',*[s for p in packets[6:] for s in (str(len(p)),*p)]]


def _normal(raw,alpha):
    f,v=_decode(raw);q,r=_quotient(v[0],f[3]);t=f[2]+q
    n=[f[k]+v[3+k] for k in (0,1)]
    K=[_multiply(_multiply(alpha,t),f[k])+v[1+k]+v[5+k]-_multiply(f[k+5],v[3+k]) for k in (0,1)]
    return n,K,r


def audit_mb_scaled_face(owner,neighbor,geometry,raw,*,face_kind='bulk',number_atol_s=1e-6,energy_atol_W=1e-15):
    g=list(map(_command,geometry));na,ea=map(_command,(number_atol_s,energy_atol_W))
    if len(g)!=5 or min(na,ea)<=0 or not(g[0]>0 and g[1]>0 and g[2]>=0 and min(g[3:])>0) or face_kind not in ('bulk','contact') or (g[2]>0)!=(face_kind=='bulk'):
        raise ValueError('scaled external geometry/budget invalid')
    a=point(owner);b=point(neighbor);f=a['frame'];h=b['frame']
    if f[5:7]!=h[5:7]:raise ValueError('scaled face requires fixed flat bands')
    coeff,saved,packets=face_values(raw);alpha,cN,cK,bandn,bandp=coeff
    G=g[0]/(g[1]/g[3]+g[2]/g[4])/Fraction(Decimal('1.602176634e-19'))
    targets=[ALPHA,G*Fraction(2,3),G*Fraction(10,9),f[5],f[6]]
    if any(abs(x-y)>128*EPS*abs(y) for x,y in zip(coeff,targets)) or min(coeff[:3])<=0:
        raise ValueError('scaled face coefficient mismatch')
    no,Ko,ro=_normal(owner,alpha);nn,Kn,rn=_normal(neighbor,alpha);expected=[ro,rn];N=[];U=[];budgets=[];residuals=[]
    for k in (0,1):
        A=Ko[k]-Kn[k];B=Ko[k]+Kn[k];D=no[k]-nn[k]
        first,r1=_quotient(_multiply(A,B),no[k])
        second,r2=_quotient(_multiply(_multiply(Kn[k],Kn[k]),D),_multiply(no[k],nn[k]))
        expected.extend((r1,r2));N.append(_multiply(A,cN));U.append(_multiply(N[-1],coeff[3+k])+_multiply(first-second,cK))
        Ap=a['K'][k]-b['K'][k];Bp=a['K'][k]+b['K'][k];Dp=a['n'][k]-b['n'][k]
        targetN=G*Fraction(2,3)*Ap
        targetU=f[5+k]*targetN+G*Fraction(10,9)*(Ap*Bp/a['n'][k]-b['K'][k]**2*Dp/(a['n'][k]*b['n'][k]))
        # This scale retains each independently stored contribution to A/D.
        av=a['values'];bv=b['values']
        Ascale=sum(map(abs,(ALPHA*(a['Tl']*f[k]-b['Tl']*h[k]),av[1+k]-bv[1+k],av[5+k]-bv[5+k],-f[5+k]*(av[3+k]-bv[3+k]))))
        Dscale=abs(f[k]-h[k])+abs(av[3+k]-bv[3+k])
        scaleN=G*Fraction(2,3)*Ascale
        scaleU=abs(f[5+k])*scaleN+G*Fraction(10,9)*(abs(Bp/a['n'][k])*Ascale+abs(b['K'][k]**2/(a['n'][k]*b['n'][k]))*Dscale)
        residuals.extend((N[-1]-targetN,U[-1]-targetU));budgets.extend((min(na,32768*EPS*scaleN),min(ea,32768*EPS*scaleU)))
    expected.extend((N[0],N[1],U[0],U[1]))
    if saved!=expected:raise ValueError('scaled face saved graph/remainders mismatch')
    if any(abs(x)>y for x,y in zip(residuals,budgets)):raise ValueError('scaled face physical flux gate failed')
    return dict(valid=True,model='full_density_rational_difference',division_remainders_checked=True,
        saved_evidence_components=5+sum(int(p[2]) for p in packets),residuals=list(map(_display,residuals)),budgets=list(map(_display,budgets)),native_physics_used=False,physical_validated=False)


def split_cell(raw):
    _tokens(raw,65535)
    evidence=_count(raw[3],4096)
    v,packets,j=_values(raw,'mb_scaled_cell_v1',8,4)
    endpoint,j=_take(raw,j,60000);clock,j=_take(raw,j)
    if j!=len(raw):raise ValueError('scaled cell trailing data')
    f,values=_decode(endpoint);end=scaled_value_fraction(clock)
    actual=sum(int(p[2]) for p in packets)+sum(int(_wire(x)[2]) for x in values)+int(clock[2])
    if actual!=evidence or _wire(end)!=clock:raise ValueError('scaled cell evidence/clock mismatch')
    return endpoint,clock,v,packets,evidence


def audit_mb_scaled_cell(old,raw,*,moments,dt_s,start_clock,particle_atol=1e-9,energy_atol_J=1e-27):
    dt,pa,ea=map(_command,(dt_s,particle_atol,energy_atol_J))
    if min(dt,pa,ea)<=0:raise ValueError('scaled positive cell duration/budgets required')
    endpoint,clock,v,packets,evidence=split_cell(raw);a=point(old);b=point(endpoint);f=a['frame']
    start=scaled_value_fraction(start_clock)
    if start<0 or list(clock)!=_wire(start+_binary113(dt)):raise ValueError('scaled exact advancing clock mismatch')
    integrated=[Fraction()]*4;scales=[Fraction()]*4
    for sign,wire in moments:
        if type(sign) is not int or sign not in (-1,1):raise ValueError('scaled cell external orientation')
        values,ps,j=_values(wire,'mb_scaled_moments_v1',4)
        if j!=len(wire):raise ValueError('scaled moment coverage')
        for k,x in enumerate(values):integrated[k]+=sign*_multiply(x,_binary113(dt));scales[k]+=abs(_multiply(x,_binary113(dt)))
    expected=a['values'].copy();rests=[];residuals=[];budgets=[]
    for k,x in enumerate(integrated):
        q,r=_quotient(x,f[4]);expected[3+k]+=q;rests.append(r)
        residuals.append(f[4]*(b['values'][3+k]-a['values'][3+k])-x)
        budgets.append(min(pa if k<2 else ea,4096*EPS*scales[k]))
    if v!=integrated+rests or b['frame']!=f or b['values']!=expected:raise ValueError('scaled cell submitted state/quotient/remainder mismatch')
    if any(abs(x)>y for x,y in zip(residuals,budgets)):raise ValueError('scaled cell particle/energy gate failed')
    return dict(valid=True,exact_state_graph_checked=True,exact_clock_checked=True,saved_evidence_components=evidence,
        residuals=list(map(_display,residuals)),budgets=list(map(_display,budgets)),native_physics_used=False,physical_validated=False)


@dataclass(frozen=True)
class _State:
    endpoint: tuple
    time_s: float
    physical_clock: tuple


def saved_state(raw):
    if not isinstance(raw,dict):raw=asdict(raw)
    if set(raw)!={'endpoint','time_s','physical_clock'}:raise ValueError('scaled saved state coverage')
    state=_State(tuple(raw['endpoint']),raw['time_s'],tuple(raw['physical_clock']));point(state.endpoint)
    clock=scaled_value_fraction(state.physical_clock)
    if list(state.physical_clock)!=_wire(clock) or type(state.time_s) is not float or not math.isfinite(state.time_s) or state.time_s<0 or clock<0 or float(clock)!=state.time_s:
        raise ValueError('scaled saved exact clock/time view mismatch')
    return state


def audit_mb_scaled_transport(old,new,report,*,faces,dt_s,particle_atol=1e-9,energy_atol_J=1e-27,number_atol_s=1e-6,energy_atol_W=1e-15):
    old=tuple(map(saved_state,old));new=tuple(map(saved_state,new));n=len(old)
    dt,pa,ea,nfa,efa=map(_command,(dt_s,particle_atol,energy_atol_J,number_atol_s,energy_atol_W))
    if min(dt,pa,ea,nfa,efa)<=0 or not 1<=n<=256 or len(new)!=n or len(faces)>512:raise ValueError('scaled independent transport coverage')
    start=old[0];clock=scaled_value_fraction(start.physical_clock);endclock=clock+_binary113(dt);end=float(endclock)
    if not math.isfinite(end) or end<=start.time_s or any(s.time_s!=start.time_s or s.physical_clock!=start.physical_clock for s in old):
        raise ValueError('scaled simultaneous advancing clocks required')
    _metadata(report,dict(scope='full_density_scaled_MB_transport',execution_backend='native',precision_bits=113,
        model='full_density_rational_difference',dt_s=float(dt_s),physical_time_advanced=True,scaled_transport_supported=True,
        collision_included=False,lattice_flux_included=False,field_work_included=False,complete_device_energy=False,physical_validated=False))
    if report['old_sha256']!=list(map(_saved_fingerprint,old)) or report['new_sha256']!=list(map(_saved_fingerprint,new)):
        raise ValueError('scaled transport state provenance mismatch')
    transfers=report['transfers'];cells=report['cells']
    if len(transfers)!=len(faces) or len(cells)!=n:raise ValueError('scaled transport proof coverage')
    moments=[[] for s in old];scales=[[Fraction()]*4 for s in old];boundary=[Fraction()]*4;seen=set();face_checks=[]
    for spec,row in zip(faces,transfers):
        if not isinstance(spec,dict) or set(spec) not in ({'owner','neighbor','geometry'},{'owner','reservoir','geometry'}):raise ValueError('scaled independent face topology')
        i=spec['owner'];contact='reservoir' in spec;j=None if contact else spec['neighbor']
        if type(i) is not int or not 0<=i<n or (not contact and (type(j) is not int or not 0<=j<n or i==j)):raise ValueError('scaled independent face index')
        if row['owner']!=i or row['neighbor']!=j:raise ValueError('scaled submitted topology mismatch')
        if not contact:
            edge=tuple(sorted((i,j)))
            if edge in seen:raise ValueError('scaled duplicate internal face')
            seen.add(edge)
        other=saved_state(spec['reservoir']) if contact else old[j]
        if other.physical_clock!=start.physical_clock or other.time_s!=start.time_s:raise ValueError('scaled contact exact clock mismatch')
        check=audit_mb_scaled_face(old[i].endpoint,other.endpoint,spec['geometry'],row['raw'],face_kind='contact' if contact else 'bulk',
            number_atol_s=number_atol_s,energy_atol_W=energy_atol_W);face_checks.append(check)
        wire=moment_wire(row['raw']);values,ps,cursor=_values(wire,'mb_scaled_moments_v1',4)
        moments[i].append((-1,wire))
        if not contact:moments[j].append((1,wire))
        for k,x in enumerate(values):
            integ=_multiply(x,_binary113(dt));scales[i][k]+=abs(integ)
            if contact:boundary[k]+=integ
            else:scales[j][k]+=abs(integ)
    checks=[];totals=[Fraction()]*6;global_budgets=[Fraction()]*6
    for i,(a,b,raw) in enumerate(zip(old,new,cells)):
        endpoint,clockwire,v,ps,e=split_cell(raw)
        if list(b.endpoint)!=endpoint or list(b.physical_clock)!=clockwire or b.time_s!=end or list(b.physical_clock)!=_wire(endclock):
            raise ValueError('scaled submitted cell/clock differs from audited output')
        check=audit_mb_scaled_cell(a.endpoint,raw,moments=moments[i],dt_s=dt_s,start_clock=a.physical_clock,
            particle_atol=particle_atol,energy_atol_J=energy_atol_J);checks.append(check)
        before=point(a.endpoint);after=point(b.endpoint);f=before['frame'];V=f[4]
        dN=[V*(after['n'][k]-before['n'][k]) for k in (0,1)]
        dU=[V*(after['K'][k]-before['K'][k]+f[5+k]*(after['n'][k]-before['n'][k])) for k in (0,1)]
        dL=V*f[3]*(after['Tl']-before['Tl'])
        r=[dN[k]-v[k] for k in (0,1)]+[dU[k]-v[2+k] for k in (0,1)]+[dL,sum(dU)+dL-sum(v[2:4])]
        base=[min(pa if k<2 else ea,4096*EPS*x) for k,x in enumerate(scales[i])];budgets=[*base,Fraction(),min(ea,sum(base[2:]))]
        if any(abs(x)>y for x,y in zip(r,budgets)):raise ValueError('scaled full physical cell energy gate failed')
        totals=[x+y for x,y in zip(totals,r)];global_budgets=[x+y for x,y in zip(global_budgets,budgets)]
    global_budgets=[min(pa if k<2 else ea,x) for k,x in enumerate(global_budgets)]
    valid=all(abs(x)<=y for x,y in zip(totals,global_budgets))
    return dict(valid=valid,faces=face_checks,cells=checks,whole_transport_particle_energy_closed=valid,
        row_order=['electron_particles','hole_particles','electron_energy','hole_energy','lattice_energy','total_energy'],
        global_residuals=list(map(_display,totals)),global_budgets=list(map(_display,global_budgets)),outward_contact_transfers=list(map(_display,boundary)),
        internal_faces_cancelled=True,exact_clock_advanced_once=True,native_physics_used=False,scaled_transport_supported=True,
        collision_included=False,complete_device_energy=False,physical_validated=False)
