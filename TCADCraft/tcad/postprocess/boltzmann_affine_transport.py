"""Independent saved affine MB face and repeated transport audits (stdlib only)."""
from dataclasses import asdict
from decimal import Decimal,localcontext
import hashlib,json,math

FIELDS=('electron_density_change','hole_density_change','electron_energy_density_change','hole_energy_density_change')
OP_NAMES=('kinetic_difference','kinetic_sum','density_difference','difference_times_sum','neighbor_kinetic_square',
    'square_times_leading_density_difference','leading_owner_inverse','owner_low_product','owner_inverse_correction',
    'leading_inverse_difference','owner_density_low_product','owner_inverse_difference_correction','neighbor_density_low_product',
    'neighbor_inverse_difference_correction','rational_difference','number','band_energy','kinetic_energy','energy')
ZERO=Decimal(0);KB=Decimal('1.380649e-23');QE=Decimal('1.602176634e-19')


def _fingerprint(state):return hashlib.sha256(json.dumps(asdict(state),sort_keys=True,separators=(',',':')).encode()).hexdigest()


class _Arithmetic:
    def __init__(self):self.eps=Decimal(2)**-112
    def bounded(self,x):return x.is_finite() and (x==0 or Decimal('1e-4000')<=abs(x)<=Decimal('1e4000'))
    def vector(self,raw):
        if not isinstance(raw,(tuple,list)) or len(raw)>4096:raise ValueError('bounded affine vector required')
        v=list(map(Decimal,raw))
        if any(not self.bounded(x) for x in v):raise ValueError('affine arithmetic component range exceeded')
        return v
    def command(self,x):
        if isinstance(x,bool) or not hasattr(x,'as_integer_ratio') or not math.isfinite(x):raise ValueError('finite independent affine command required')
        n,d=x.as_integer_ratio();return Decimal(n)/Decimal(d)
    def binary(self,raw):
        x=Decimal(raw)
        if not self.bounded(x):raise ValueError('bounded affine binary value required')
        if x==0:return ZERO
        n,d=abs(x).as_integer_ratio();e=n.bit_length()-d.bit_length()
        if (n<d<<e) if e>=0 else (n<<(-e)<d):e-=1
        shift=112-e;n,d=(n<<shift,d) if shift>=0 else (n,d<<(-shift))
        h,r=divmod(n,d)
        if 2*r>d or (2*r==d and h%2):h+=1
        v=Decimal(h)*Decimal(2)**(e-112)
        if not self.bounded(v):raise ValueError('affine binary arithmetic range exceeded')
        return v if x>0 else -v
    def bvector(self,raw):return list(map(self.binary,raw))
    def bsum(self,raw):return sum(self.bvector(raw),ZERO)
    def canonical(self,raw):
        v=self.bvector(raw)
        return all(v) and all(abs(a)<=self.eps*abs(b) for a,b in zip(v,v[1:])) if v else True
    def products(self,raw,t):
        result=[]
        for x in self.bvector(raw):
            if x:
                h=self.binary(x*t);l=self.binary(x*t-h)
                if not h:raise ValueError('affine integrated product underflow')
                result.extend(y for y in (h,l) if y)
        return result
    def quotients(self,raw,V):
        result=[]
        for x in self.bvector(raw):
            if x:
                h=self.binary(x/V);r=self.binary(x-h*V);l=self.binary(r/V)
                if not h or (r and not l):raise ValueError('affine volume quotient underflow')
                result.append(h)
                if l:result.append(l)
        return result


def _point(state,m):
    affine=hasattr(state,'anchor');anchor=state.anchor if affine else state
    raw=tuple(getattr(state,key) for key in FIELDS) if affine else ((),(),(),())
    change=[m.vector(v) for v in raw];f=m.vector(anchor.frame)
    if not 10<=len(f)<=256 or any(not Decimal('1e-1000')<=f[j]<=Decimal('1e1000') for j in (0,1,3,4)):
        raise ValueError('affine anchor frame range invalid')
    if not 1<f[2]<100000 or not 1<f[7]<f[8]<100000 or max(abs(f[5]),abs(f[6]))>Decimal('1e1000'):
        raise ValueError('affine anchor temperature/band domain invalid')
    if isinstance(state.time_s,bool) or not math.isfinite(state.time_s) or state.time_s<0 or (affine and state.time_s<=anchor.time_s):
        raise ValueError('affine endpoint clock invalid')
    excess=[m.vector(anchor.electron_excess),m.vector(anchor.hole_excess)]
    if not all(excess):raise ValueError('nonempty affine anchor excess required')
    Tl=f[2]+sum(f[9:],ZERO)/f[3];alpha=Decimal('1.5')*KB;n=[];K=[];ts=[Tl]
    for k in range(2):
        density=f[k]+sum(change[k],ZERO)
        if not Decimal('1e-1000')<=density<=Decimal('1e1000'):raise ValueError('actual affine density outside positive range')
        kinetic=alpha*Tl*f[k]+sum(excess[k],ZERO)+sum(change[k+2],ZERO)-f[k+5]*sum(change[k],ZERO)
        n.append(density);K.append(kinetic);ts.append(kinetic/(alpha*density))
    # The anchor is a coordinate baseline inside an affine state. Only the
    # complete submitted n/K/Tl define physical temperatures. For a standalone
    # anchor the increments are empty, so the same actual-state check applies.
    env=128*m.eps*max(1,*map(abs,ts))
    if any(t<f[7]-env or t>f[8]+env for t in ts):raise ValueError('actual affine temperature outside bounds')
    return dict(anchor=anchor,raw=raw,change=change,frame=f,excess=excess,Tl=Tl,n=n,K=K,temperatures=ts)


def _metadata(report,values):
    if any(type(report.get(k)) is not type(v) or report.get(k)!=v for k,v in values.items()):raise ValueError('affine scope metadata mismatch')


def audit_affine_mb_face(owner,neighbor,report,*,geometry,face_kind='bulk',number_atol_s=1e-6,energy_atol_W=1e-15):
    with localcontext() as ctx:
        ctx.prec=10000;m=_Arithmetic();a=_point(owner,m);b=_point(neighbor,m);f=a['frame'];h=b['frame']
        _metadata(report,dict(scope='flat_MB_affine_density_energy_face',execution_backend='native',precision_bits=113,
            face_kind=face_kind,time_s=owner.time_s,inverse_density_model='first_order_inverse_density_difference',
            affine_endpoint_supported=True,physical_time_advanced=False,device_statistics_selected=False,complete_device_energy=False,physical_validated=False))
        if owner.time_s!=neighbor.time_s or report.get('owner_sha256')!=_fingerprint(owner) or report.get('neighbor_sha256')!=_fingerprint(neighbor):
            raise ValueError('affine face endpoint provenance/clock mismatch')
        af=a['anchor'].frame;bf=b['anchor'].frame
        if (af[2],af[3],af[9:])!=(bf[2],bf[3],bf[9:]) or any(f[j]!=h[j] for j in (5,6)):raise ValueError('affine common lattice/bands required')
        g=list(map(m.command,geometry));limits=list(map(m.command,(number_atol_s,energy_atol_W)))
        if len(g)!=5 or min(limits)<=0 or not(g[0]>0 and g[1]>0 and g[2]>=0 and min(g[3:])>0) or face_kind not in ('bulk','contact') or (g[2]>0)!=(face_kind=='bulk'):
            raise ValueError('affine external geometry/budget invalid')
        rg=m.vector(report.get('geometry'))
        if len(rg)!=5 or any(abs(x-y)>16*m.eps*abs(y) for x,y in zip(rg,g)):raise ValueError('affine independent geometry mismatch')
        alpha=Decimal(report['alpha']);inverse=Decimal(report['inverse_Cv']);t=m.vector(report['thermal_expansion'])
        if not m.bounded(alpha) or not m.bounded(inverse) or alpha<=0 or inverse<=0:raise ValueError('affine thermal scales invalid')
        valid=abs(alpha-Decimal('1.5')*KB)<=128*m.eps*KB and abs(inverse-1/f[3])<=128*m.eps/f[3]
        valid &= m.canonical(report['thermal_expansion']) and m.bsum(report['thermal_expansion'])==m.binary(af[2])+m.binary(inverse)*m.bsum(af[9:])
        valid &= abs(sum(t,ZERO)-a['Tl'])<=Decimal('1e-25')*max(1,abs(a['Tl']))
        G=g[0]/(g[1]/g[3]+g[2]/g[4])/QE;carriers=report.get('carriers');checks=[];components=len(t)
        if not isinstance(carriers,list) or len(carriers)!=2:raise ValueError('affine two-carrier coverage invalid')
        for k,row in enumerate(carriers):
            c=m.vector(row['coefficients']);norm=row['normalization']
            if len(c)!=8 or not isinstance(norm,list) or len(norm)!=4:raise ValueError('affine coefficient/normalization coverage invalid')
            for raw in norm:components+=len(m.vector(raw))
            targets=[]
            for point,anchorframe in ((a,af),(b,bf)):targets.append(m.binary(anchorframe[k])+m.bsum(point['raw'][k]))
            for point,anchorframe in ((a,af),(b,bf)):
                targets.append(m.binary(alpha)*m.bsum(report['thermal_expansion'])*m.binary(anchorframe[k])+
                    m.bsum((point['anchor'].electron_excess,point['anchor'].hole_excess)[k])+m.bsum(point['raw'][k+2])-
                    m.binary(anchorframe[k+5])*m.bsum(point['raw'][k]))
            norm_ok=all(m.canonical(raw) and m.bsum(raw)==target for raw,target in zip(norm,targets))
            if not norm[0] or not norm[1] or m.binary(norm[0][-1])<=0 or m.binary(norm[1][-1])<=0:raise ValueError('affine positive leading density required')
            ro=1/m.binary(norm[0][-1]);rn=1/m.binary(norm[1][-1])
            expected=[G*2/3,f[k+5],G*10/9,ro,-ro*ro,-ro*rn,-ro*ro,rn*rn]
            coefficients_ok=all(abs(x-y)<=256*m.eps*abs(y) for x,y in zip(c,expected))
            ops=row.get('operations')
            if not isinstance(ops,list) or len(ops)!=19 or [r.get('name') for r in ops]!=list(OP_NAMES):raise ValueError('affine operation DAG coverage/order invalid')
            values=[];operations_ok=True;no,nn,Ko,Kn=map(m.bsum,norm);Lo=m.bsum(norm[0][:-1]);Ln=m.bsum(norm[1][:-1]);bc=m.bvector(row['coefficients'])
            for i,record in enumerate(ops):
                raw=record['value'];components+=len(m.vector(raw));v=values
                targets=(lambda:Ko-Kn,lambda:Ko+Kn,lambda:no-nn,lambda:v[0]*v[1],lambda:Kn*Kn,lambda:v[4]*(m.binary(norm[0][-1])-m.binary(norm[1][-1])),
                    lambda:v[3]*bc[3],lambda:v[3]*Lo,lambda:v[7]*bc[4],lambda:v[5]*bc[5],lambda:v[4]*Lo,
                    lambda:v[10]*bc[6],lambda:v[4]*Ln,lambda:v[12]*bc[7],lambda:v[6]+v[8]+v[9]+v[11]+v[13],
                    lambda:v[0]*bc[0],lambda:v[15]*bc[1],lambda:v[14]*bc[2],lambda:v[16]+v[17])
                value=m.bsum(raw);operations_ok &= m.canonical(raw) and value==targets[i]();values.append(value)
            if components>4096:raise ValueError('affine face total component budget exceeded')
            if row.get('number_expansion')!=ops[15]['value'] or row.get('energy_expansion')!=ops[18]['value']:raise ValueError('affine submitted moments differ from operation DAG')
            dn0=f[k]-h[k];dd=sum(a['excess'][k],ZERO)-sum(b['excess'][k],ZERO)
            du=sum(a['change'][k+2],ZERO)-sum(b['change'][k+2],ZERO);ddn=sum(a['change'][k],ZERO)-sum(b['change'][k],ZERO)
            A=a['K'][k]-b['K'][k];B=a['K'][k]+b['K'][k];D=a['n'][k]-b['n'][k];nO=a['n'][k];nN=b['n'][k];K=b['K'][k]
            Ascale=sum(map(abs,(Decimal('1.5')*KB*a['Tl']*dn0,dd,du,-f[k+5]*ddn)),ZERO);Dscale=abs(dn0)+abs(ddn)
            N=G*2/3*A;E=f[k+5]*N+G*10/9*(A*B/nO-K*K*D/nO/nN)
            scales=[G*2/3*Ascale,abs(f[k+5])*G*2/3*Ascale+G*10/9*(abs(B/nO)*Ascale+abs(K*K/nO/nN)*Dscale)]
            residual=[sum(map(Decimal,row['number_expansion']),ZERO)-N,sum(map(Decimal,row['energy_expansion']),ZERO)-E]
            budgets=[min(limit,32768*m.eps*scale) for limit,scale in zip(limits,scales)]
            physical_ok=all(abs(x)<=budget for x,budget in zip(residual,budgets))
            passed=norm_ok and coefficients_ok and operations_ok and physical_ok;valid &= passed
            checks.append(dict(valid=bool(passed),normalization_binary_exact=bool(norm_ok),coefficients_valid=bool(coefficients_ok),
                operation_DAG_binary_exact=bool(operations_ok),physical_flux_valid=bool(physical_ok),
                residuals=[format(x,'.12E') for x in residual],budgets=[format(x,'.12E') for x in budgets]))
        return dict(valid=bool(valid),carriers=checks,component_count=components,native_physics_used=False,
            affine_endpoint_supported=True,physical_time_advanced=False,complete_device_energy=False,physical_validated=False)


def audit_mb_affine_transport(old,new,report,*,faces,dt_s,particle_atol=1e-9,energy_atol_J=1e-27,number_atol_s=1e-6,energy_atol_W=1e-15):
    with localcontext() as ctx:
        ctx.prec=10000;m=_Arithmetic();t,na,ea,nfa,efa=map(m.command,(dt_s,particle_atol,energy_atol_J,number_atol_s,energy_atol_W))
        if min(t,na,ea,nfa,efa)<=0 or not 1<=len(old)<=256 or len(new)!=len(old) or len(faces)>512:raise ValueError('bounded independent affine transport problem required')
        points=[_point(s,m) for s in old];end=old[0].time_s+float(dt_s)
        if not math.isfinite(end) or end<=old[0].time_s or any(s.time_s!=old[0].time_s for s in old):raise ValueError('simultaneous advancing affine clocks required')
        _metadata(report,dict(scope='repeated_flat_MB_affine_transport',execution_backend='native',precision_bits=113,time_s=end,
            physical_time_advanced=True,repeat_transport_supported=True,device_statistics_selected=False,field_work_inferred=False,
            lattice_flux_included=False,complete_device_energy=False,physical_validated=False))
        if abs(Decimal(report['dt_s'])-t)>16*m.eps*t or report.get('old_sha256')!=list(map(_fingerprint,old)) or report.get('new_sha256')!=list(map(_fingerprint,new)):
            raise ValueError('affine state/time provenance mismatch')
        transfers=report.get('transfers');cells=report.get('cells')
        if not isinstance(transfers,list) or len(transfers)!=len(faces) or not isinstance(cells,list) or len(cells)!=len(old):raise ValueError('affine transport coverage mismatch')
        signed=[[[] for _ in range(4)] for _ in old];boundary=[ZERO]*4;seen=set();checks=[];valid=True
        for spec,record in zip(faces,transfers):
            if not isinstance(spec,dict) or set(spec) not in ({'owner','neighbor','geometry'},{'owner','reservoir','geometry'}):raise ValueError('independent affine topology required')
            i=spec['owner'];contact='reservoir' in spec;j=None if contact else spec['neighbor']
            if type(i) is not int or not 0<=i<len(old) or (not contact and (type(j) is not int or not 0<=j<len(old) or i==j)):raise ValueError('affine topology index invalid')
            if not contact:
                edge=tuple(sorted((i,j)))
                if edge in seen:raise ValueError('duplicate affine internal face')
                seen.add(edge)
            if type(record.get('owner')) is not int or record['owner']!=i or record.get('neighbor')!=j or (j is not None and type(record['neighbor']) is not int):raise ValueError('affine submitted topology mismatch')
            check=audit_affine_mb_face(old[i],spec['reservoir'] if contact else old[j],record['moment'],geometry=spec['geometry'],
                face_kind='contact' if contact else 'bulk',number_atol_s=number_atol_s,energy_atol_W=energy_atol_W)
            valid &= check['valid'];integ=record['integrated']
            if not isinstance(integ,list) or len(integ)!=4:raise ValueError('affine integral coverage mismatch')
            source=[record['moment']['carriers'][k][key] for key in ('number_expansion','energy_expansion') for k in range(2)];exact=True
            for k,(raw,flux) in enumerate(zip(integ,source)):
                values=m.vector(raw);exact &= m.bvector(raw)==m.products(flux,m.binary(report['dt_s']))
                signed[i][k].extend(-x for x in values)
                if contact:boundary[k]+=sum(values,ZERO)
                else:signed[j][k].extend(values)
            valid &= exact;checks.append(dict(face_valid=check['valid'],integrals_binary_exact=bool(exact)))
        changes=[ZERO]*4;scales=[ZERO]*4;cell_checks=[]
        for i,(state,point,cell) in enumerate(zip(new,points,cells)):
            current=_point(state,m)
            if asdict(current['anchor'])!=asdict(point['anchor']) or state.time_s!=end:raise ValueError('affine anchor/history/clock changed')
            added=[]
            for oldraw,newraw in zip(point['raw'],current['raw']):
                if tuple(newraw[:len(oldraw)])!=tuple(oldraw):raise ValueError('affine prior increment prefix altered')
                added.append(newraw[len(oldraw):])
            V=point['frame'][4];bV=m.binary(point['anchor'].frame[4]);exact=all(m.bvector(raw)==m.quotients(target,bV) for raw,target in zip(added,signed[i]))
            residual=[];budgets=[]
            for k,(raw,target) in enumerate(zip(added,signed[i])):
                change=V*sum(map(Decimal,raw),ZERO);scale=sum(map(abs,target),ZERO)
                residual.append(change-sum(target,ZERO));budgets.append(min(na if k<2 else ea,4096*m.eps*scale));changes[k]+=change;scales[k]+=scale
            views=m.vector(cell.get('temperatures_K'));views_ok=len(views)==3 and all(abs(a-b)<=Decimal('1e-25')*max(1,abs(b)) for a,b in zip(views,current['temperatures']))
            closed=all(abs(x)<=budget for x,budget in zip(residual,budgets));valid &= exact and closed and views_ok
            cell_checks.append(dict(quotients_binary_exact=bool(exact),physical_rows_closed=bool(closed),temperatures_valid=bool(views_ok),
                residuals=[format(x,'.12E') for x in residual],budgets=[format(x,'.12E') for x in budgets]))
        residual=[x+y for x,y in zip(changes,boundary)];budgets=[min(na if k<2 else ea,4096*m.eps*scale) for k,scale in enumerate(scales)]
        closed=all(abs(x)<=budget for x,budget in zip(residual,budgets));valid &= closed
        return dict(valid=bool(valid),faces=checks,cells=cell_checks,global_particle_energy_closed=bool(closed),
            global_residuals=[format(x,'.12E') for x in residual],global_budgets=[format(x,'.12E') for x in budgets],
            outward_contact_transfers=[format(x,'.12E') for x in boundary],native_physics_used=False,repeat_transport_supported=True,
            complete_device_energy=False,physical_validated=False)
