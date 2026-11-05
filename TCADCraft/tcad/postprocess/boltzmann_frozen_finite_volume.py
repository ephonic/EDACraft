"""Saved FV audit: standard-library binary arithmetic and physical ledgers only."""
from dataclasses import asdict
from decimal import Decimal,localcontext
import hashlib,json,math
from tcad.postprocess.boltzmann_expanded_flat_face import audit_expanded_mb_flat_face

FIELDS=('electron_density_change','hole_density_change','electron_energy_density_change','hole_energy_density_change')


def audit_mb_frozen_finite_volume(old,new,report,*,faces,dt_s,particle_atol=1e-9,energy_atol_J=1e-27,
                                 number_atol_s=1e-6,energy_atol_W=1e-15):
    fingerprint=lambda state:hashlib.sha256(json.dumps(asdict(state),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    def command(x):
        if isinstance(x,bool) or not hasattr(x,'as_integer_ratio') or not math.isfinite(x):raise ValueError('finite independent FV command required')
        n,d=x.as_integer_ratio();return Decimal(n)/Decimal(d)
    with localcontext() as ctx:
        ctx.prec=10000;eps=Decimal(2)**-112;zero=Decimal(0)
        def bounded(x):return x.is_finite() and (x==0 or Decimal('1e-4000')<=abs(x)<=Decimal('1e4000'))
        def vector(raw):
            if not isinstance(raw,(list,tuple)) or len(raw)>4096:raise ValueError('bounded FV expansion required')
            v=list(map(Decimal,raw))
            if any(not bounded(x) for x in v):raise ValueError('FV component outside arithmetic range')
            return v
        def binary(raw):
            x=Decimal(raw)
            if not bounded(x):raise ValueError('bounded native FV value required')
            if x==0:return zero
            n,d=abs(x).as_integer_ratio();e=n.bit_length()-d.bit_length()
            if (n<d<<e) if e>=0 else (n<<(-e)<d):e-=1
            shift=112-e;n,d=(n<<shift,d) if shift>=0 else (n,d<<(-shift))
            h,r=divmod(n,d)
            if 2*r>d or (2*r==d and h%2):h+=1
            result=Decimal(h)*Decimal(2)**(e-112)
            if not bounded(result):raise ValueError('FV binary operation outside normal range')
            return result if x>0 else -result
        def bvector(raw):return list(map(binary,raw))
        def products(raw,t):
            output=[]
            for x in bvector(raw):
                if x!=0:
                    h=binary(x*t);l=binary(x*t-h)
                    if h==0:raise ValueError('FV product underflow')
                    output.extend(y for y in (h,l) if y!=0)
            return output
        def quotients(raw,v):
            output=[]
            for x in bvector(raw):
                if x!=0:
                    h=binary(x/v);r=binary(x-h*v);l=binary(r/v)
                    if h==0 or (r!=0 and l==0):raise ValueError('FV quotient underflow')
                    output.append(h)
                    if l!=0:output.append(l)
            return output
        t,na,ea,nfa,efa=map(command,(dt_s,particle_atol,energy_atol_J,number_atol_s,energy_atol_W))
        if min(t,na,ea,nfa,efa)<=0 or not 1<=len(old)<=256 or len(new)!=len(old) or len(faces)>512:
            raise ValueError('positive bounded FV audit problem required')
        end=old[0].time_s+float(dt_s)
        if not math.isfinite(end) or end<=old[0].time_s or any(s.time_s!=old[0].time_s for s in old):
            raise ValueError('strictly advancing simultaneous FV clocks required')
        metadata=dict(scope='one_frozen_flat_MB_finite_volume_transaction',execution_backend='native',precision_bits=113,
            time_s=end,physical_time_advanced=True,repeat_transport_supported=False,device_statistics_selected=False,
            field_work_inferred=False,lattice_flux_included=False,complete_device_energy=False,physical_validated=False)
        if any(type(report.get(k)) is not type(v) or report.get(k)!=v for k,v in metadata.items()):raise ValueError('FV scope/metadata mismatch')
        if abs(Decimal(report['dt_s'])-t)>16*eps*t:raise ValueError('FV independent time-step mismatch')
        if report.get('old_sha256')!=[fingerprint(s) for s in old] or report.get('new_sha256')!=[fingerprint(s) for s in new]:
            raise ValueError('FV state provenance mismatch')
        transfers=report.get('transfers');cells=report.get('cells')
        if not isinstance(transfers,list) or len(transfers)!=len(faces) or not isinstance(cells,list) or len(cells)!=len(old):
            raise ValueError('FV face/cell coverage mismatch')
        signed=[[[] for _ in range(4)] for _ in old];boundary=[zero]*4;seen=set();valid=True;face_checks=[]
        bt=binary(report['dt_s'])
        for spec,record in zip(faces,transfers):
            if not isinstance(spec,dict) or set(spec) not in ({'owner','neighbor','geometry'},{'owner','reservoir','geometry'}):
                raise ValueError('independent FV face specification required')
            i=spec['owner'];contact='reservoir' in spec;j=None if contact else spec['neighbor']
            if type(i) is not int or not 0<=i<len(old) or (not contact and (type(j) is not int or not 0<=j<len(old) or i==j)):
                raise ValueError('FV topology index invalid')
            if not contact:
                edge=tuple(sorted((i,j)))
                if edge in seen:raise ValueError('duplicate FV internal face')
                seen.add(edge)
            if type(record.get('owner')) is not int or record['owner']!=i or record.get('neighbor')!=j or (j is not None and type(record['neighbor']) is not int):
                raise ValueError('FV topology differs from independent face')
            endpoint=spec['reservoir'] if contact else old[j]
            face=audit_expanded_mb_flat_face(old[i],endpoint,record['moment'],geometry=spec['geometry'],
                face_kind='contact' if contact else 'bulk',number_atol_s=number_atol_s,energy_atol_W=energy_atol_W)
            valid &= face['valid'];integrated=record.get('integrated')
            if not isinstance(integrated,list) or len(integrated)!=4:raise ValueError('FV transfer coverage mismatch')
            source=[record['moment']['carriers'][k][key] for key in ('number_expansion','energy_expansion') for k in range(2)]
            exact=True
            for k,(raw,flux) in enumerate(zip(integrated,source)):
                values=vector(raw);exact &= bvector(raw)==products(flux,bt)
                signed[i][k].extend(-x for x in values)
                if contact:boundary[k]+=sum(values,zero)
                else:signed[j][k].extend(values)
            valid &= exact;face_checks.append(dict(moment_valid=face['valid'],integrals_binary_exact=bool(exact)))
        global_change=[zero]*4;global_scale=[zero]*4;cell_checks=[];alpha=Decimal('1.5')*Decimal('1.380649e-23')
        for i,(anchor,state,cell) in enumerate(zip(old,new,cells)):
            if asdict(state.anchor)!=asdict(anchor) or state.time_s!=end:raise ValueError('FV anchor/history/clock changed')
            f=vector(anchor.frame)
            if not 10<=len(f)<=256 or any(not Decimal('1e-1000')<=f[k]<=Decimal('1e1000') for k in (0,1,3,4)):
                raise ValueError('FV anchor frame outside positive range')
            if not 1<f[2]<100000 or not 1<f[7]<f[8]<100000 or max(abs(f[5]),abs(f[6]))>Decimal('1e1000'):
                raise ValueError('FV anchor domain invalid')
            # The no-face case still independently checks all anchor components.
            old_excess=[vector(anchor.electron_excess),vector(anchor.hole_excess)]
            if not all(old_excess):raise ValueError('FV anchor excess coverage invalid')
            increments=[vector(getattr(state,key)) for key in FIELDS];V=f[4];bV=binary(anchor.frame[4])
            exact=all(bvector(getattr(state,key))==quotients(raw,bV) for key,raw in zip(FIELDS,signed[i]))
            residual=[];budgets=[]
            for k,(values,raw) in enumerate(zip(increments,signed[i])):
                target=sum(raw,zero);change=V*sum(values,zero);scale=sum(map(abs,raw),zero)
                residual.append(change-target);budgets.append(min(na if k<2 else ea,Decimal(4096)*eps*scale))
                global_change[k]+=change;global_scale[k]+=scale
            Tl=f[2]+sum(f[9:],zero)/f[3];ts=[Tl];old_ts=[Tl];domain=True
            for k in range(2):
                n=f[k]+sum(increments[k],zero);d=sum(old_excess[k],zero)
                if not Decimal('1e-1000')<=n<=Decimal('1e1000'):domain=False
                if n<=0:raise ValueError('nonpositive submitted FV density')
                excess=d+sum(increments[k+2],zero)-sum(increments[k],zero)*(f[k+5]+alpha*Tl)
                ts.append(Tl+excess/(alpha*n));old_ts.append(Tl+d/(alpha*f[k]))
            views=vector(cell.get('temperatures_K'))
            envelope=Decimal(128)*eps*max(1,*map(abs,ts),*map(abs,old_ts))
            domain &= all(f[7]-envelope<=x<=f[8]+envelope for x in (*old_ts,*ts))
            views_ok=len(views)==3 and all(abs(a-b)<=Decimal('1e-25')*max(1,abs(b)) for a,b in zip(views,ts))
            closed=all(abs(r)<=b for r,b in zip(residual,budgets));valid &= exact and closed and domain and views_ok
            cell_checks.append(dict(quotients_binary_exact=bool(exact),physical_rows_closed=bool(closed),domain_valid=bool(domain),
                temperatures_valid=bool(views_ok),residuals=[str(x) for x in residual],budgets=[str(x) for x in budgets]))
        residual=[x+y for x,y in zip(global_change,boundary)]
        budgets=[min(na if k<2 else ea,Decimal(4096)*eps*scale) for k,scale in enumerate(global_scale)]
        closed=all(abs(x)<=b for x,b in zip(residual,budgets));valid &= closed
        return dict(valid=bool(valid),faces=face_checks,cells=cell_checks,native_physics_used=False,
            global_particle_energy_closed=bool(closed),global_residuals=[str(x) for x in residual],global_budgets=[str(x) for x in budgets],
            outward_contact_transfers=[str(x) for x in boundary],physical_time_advanced=True,
            repeat_transport_supported=False,complete_device_energy=False,physical_validated=False)
