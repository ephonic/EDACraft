"""Independent nonisothermal face and transport audits, stdlib only."""
from dataclasses import asdict
from decimal import Decimal,localcontext
import math
from tcad.postprocess.boltzmann_affine_transport import _Arithmetic,_point,_metadata,_fingerprint,OP_NAMES,ZERO,KB,QE

def audit_nonisothermal_mb_face(owner,neighbor,report,*,geometry,face_kind='bulk',number_atol_s=1e-6,energy_atol_W=1e-15):
    with localcontext() as ctx:
        ctx.prec=10000;m=_Arithmetic();a=_point(owner,m);b=_point(neighbor,m);f=a['frame'];h=b['frame']
        _metadata(report,dict(scope='flat_MB_nonisothermal_affine_face',execution_backend='native',precision_bits=113,
            face_kind=face_kind,time_s=owner.time_s,lattice_normalization='compensated_capacity_quotients',inverse_density_model='first_order_inverse_density_difference',
            affine_endpoint_supported=True,lattice_heterogeneity_supported=True,lattice_flux_included=False,physical_time_advanced=False,device_statistics_selected=False,complete_device_energy=False,physical_validated=False))
        if owner.time_s!=neighbor.time_s or report.get('owner_sha256')!=_fingerprint(owner) or report.get('neighbor_sha256')!=_fingerprint(neighbor):
            raise ValueError('affine face endpoint provenance/clock mismatch')
        af=a['anchor'].frame;bf=b['anchor'].frame
        if any(f[j]!=h[j] for j in (5,6)):raise ValueError('nonisothermal flat bands required')
        g=list(map(m.command,geometry));limits=list(map(m.command,(number_atol_s,energy_atol_W)))
        if len(g)!=5 or min(limits)<=0 or not(g[0]>0 and g[1]>0 and g[2]>=0 and min(g[3:])>0) or face_kind not in ('bulk','contact') or (g[2]>0)!=(face_kind=='bulk'):
            raise ValueError('affine external geometry/budget invalid')
        rg=m.vector(report.get('geometry'))
        if len(rg)!=5 or any(abs(x-y)>16*m.eps*abs(y) for x,y in zip(rg,g)):raise ValueError('affine independent geometry mismatch')
        alpha=Decimal(report['alpha']);thermal=report['thermal_expansions'];quotients=report['lattice_quotients']
        if not isinstance(thermal,list) or len(thermal)!=2 or not isinstance(quotients,list) or len(quotients)!=2 or not m.bounded(alpha) or alpha<=0:
            raise ValueError('nonisothermal thermal/quotient endpoint coverage invalid')
        t=[m.vector(raw) for raw in thermal];q=[m.vector(raw) for raw in quotients]
        valid=abs(alpha-Decimal('1.5')*KB)<=128*m.eps*KB
        for point,quot,raw in zip((a,b),quotients,thermal):
            anchorframe=point['anchor'].frame
            valid &= m.bvector(quot)==m.quotients(anchorframe[9:],m.binary(anchorframe[3]))
            valid &= m.canonical(raw) and m.bsum(raw)==m.binary(anchorframe[2])+m.bsum(quot)
            valid &= abs(sum(map(Decimal,raw),ZERO)-point['Tl'])<=Decimal('1e-25')*max(1,abs(point['Tl']))
        G=g[0]/(g[1]/g[3]+g[2]/g[4])/QE;carriers=report.get('carriers');checks=[];components=sum(map(len,t))+sum(map(len,q))
        if not isinstance(carriers,list) or len(carriers)!=2:raise ValueError('affine two-carrier coverage invalid')
        for k,row in enumerate(carriers):
            c=m.vector(row['coefficients']);norm=row['normalization']
            if len(c)!=8 or not isinstance(norm,list) or len(norm)!=4:raise ValueError('affine coefficient/normalization coverage invalid')
            for raw in norm:components+=len(m.vector(raw))
            targets=[]
            for point,anchorframe in ((a,af),(b,bf)):targets.append(m.binary(anchorframe[k])+m.bsum(point['raw'][k]))
            for point,anchorframe,thermal_raw in ((a,af,thermal[0]),(b,bf,thermal[1])):
                targets.append(m.binary(alpha)*m.bsum(thermal_raw)*m.binary(anchorframe[k])+
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
            Ascale=sum(map(abs,(Decimal('1.5')*KB*(a['Tl']-b['Tl'])*f[k],Decimal('1.5')*KB*b['Tl']*dn0,dd,du,-f[k+5]*ddn)),ZERO);Dscale=abs(dn0)+abs(ddn)
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
            affine_endpoint_supported=True,lattice_heterogeneity_supported=True,lattice_flux_included=False,physical_time_advanced=False,complete_device_energy=False,physical_validated=False)


def audit_mb_nonisothermal_transport(old,new,report,*,faces,dt_s,particle_atol=1e-9,energy_atol_J=1e-27,number_atol_s=1e-6,energy_atol_W=1e-15):
    with localcontext() as ctx:
        ctx.prec=10000;m=_Arithmetic();t,na,ea,nfa,efa=map(m.command,(dt_s,particle_atol,energy_atol_J,number_atol_s,energy_atol_W))
        if min(t,na,ea,nfa,efa)<=0 or not 1<=len(old)<=256 or len(new)!=len(old) or len(faces)>512:raise ValueError('bounded independent affine transport problem required')
        points=[_point(s,m) for s in old];end=old[0].time_s+float(dt_s)
        if not math.isfinite(end) or end<=old[0].time_s or any(s.time_s!=old[0].time_s for s in old):raise ValueError('simultaneous advancing affine clocks required')
        _metadata(report,dict(scope='repeated_flat_MB_nonisothermal_transport',execution_backend='native',precision_bits=113,time_s=end,
            physical_time_advanced=True,repeat_transport_supported=True,lattice_heterogeneity_supported=True,device_statistics_selected=False,field_work_inferred=False,
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
            check=audit_nonisothermal_mb_face(old[i],spec['reservoir'] if contact else old[j],record['moment'],geometry=spec['geometry'],
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
