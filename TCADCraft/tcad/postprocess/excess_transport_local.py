"""Independent Decimal replay of a prescribed-moment local Schur complement.

This verifies assembly, not the origin of supplied DOS/source/face moments.
Unlike the native logarithmic logistic weights, the reference forms tau and
uses tau/(tau+dt), dt/(tau+dt) at 90 decimal digits. No native operator is used.
"""
from decimal import Decimal, localcontext
from tcad.physics.excess_transport_local import FIELDS, SCOPE


def audit_excess_transport_local(cells, faces, timestep, report, *,
                                particle_atol='1e-9', energy_atol_J='1e-27', rtol='1e-26'):
    with localcontext() as ctx:
        ctx.prec=90
        def number(value):
            if not isinstance(value,str):raise ValueError('finite decimal strings required')
            result=Decimal(value)
            if not result.is_finite():raise ValueError('finite decimal strings required')
            return result
        c=[list(map(number,row)) for row in cells];f=[list(map(number,row)) for row in faces]
        dt=number(timestep);pa=number(particle_atol);ea=number(energy_atol_J);rt=number(rtol)
        if not c or any(len(row)!=34 for row in c) or any(len(row)!=13 for row in f) or min(dt,pa,ea,rt)<=0:
            raise ValueError('positive budgets, timestep and exact row coverage required')
        nc=len(c);nf=len(f);zero=Decimal(0);one=Decimal(1);q=Decimal('1.602176634e-19')
        particles=[[zero,zero] for _ in c];work=[[zero,zero] for _ in c]
        transport=[[zero,zero] for _ in c];heat=[zero for _ in c];fourier=[]
        for row in c:
            if any(row[k]<=0 for k in (0,1,2,3,4,5,12,13,16,17,18,19,22,23,24)):
                raise ValueError('positive state and material coefficients required')
        for row in f:
            i,j=row[:2]
            if i!=i.to_integral_value() or j!=j.to_integral_value() or not 0<=i<nc or not -1<=j<nc or i==j:
                raise ValueError('face indices invalid')
            i=int(i);j=int(j)
            if row[8]<=0 or row[9]<=0 or (row[10]<=0 if j>=0 else row[10]!=0) or row[12] not in (0,1):
                raise ValueError('face geometry or mode invalid')
            if (row[12]==1 and (j>=0 or row[11]<=0)) or (row[12]==0 and row[11]!=0):
                raise ValueError('face bath invalid')
            h=(row[8]/(row[9]/c[i][16]+row[10]/c[j][16])*(c[i][5]-c[j][5]) if j>=0 else
               row[8]*c[i][16]/row[9]*(c[i][5]-row[11]) if row[12]==1 else zero)
            fourier.append(h)
            for node,sign in ((i,one),(j,-one)) if j>=0 else ((i,one),):
                heat[node]+=dt*sign*h
                delta=(c[node][14]+c[node][15]-row[6]-row[7])/2
                for s,charge in ((0,-q),(1,q)):
                    particles[node][s]+=dt*sign*row[2+s]
                    transport[node][s]+=dt*sign*row[4+s]
                    work[node][s]+=charge*dt*sign*row[2+s]*delta
        reference=[];scales=[]
        for i,row in enumerate(c):
            V=row[12];out=[zero]*20;scale=[zero]*20
            out[6]=V*row[13]*(row[5]-row[2])
            energy_scale=V*(abs(row[6])+abs(row[7])+abs(row[8])+abs(row[9])+abs(row[10])+abs(row[11])+
                            row[13]*(row[2]+row[5]))+sum(abs(v) for v in row[29:34])+sum(abs(v) for v in transport[i]+work[i])+abs(heat[i])
            for s in (0,1):
                eq=6+3*s;law=17+5*s
                tau=(row[law].ln()+row[law+3]*(row[5]/row[law+1]).ln()+
                     row[law+4]*(row[3+s]/row[law+2]).ln()).exp()
                if not 0<float(tau)<float('inf'):raise ValueError('positive float64 relaxation range required')
                retained=tau/(tau+dt);lost=dt/(tau+dt)
                difference=row[eq]-row[eq+1]+row[eq+2]
                net=row[29+s]+row[32+s]+work[i][s]-transport[i][s]
                drive=difference+net/V;excess=retained*drive;exchange=V*lost*drive
                storage=V*(-difference+excess)
                out[s]=V*(row[3+s]-row[s])+particles[i][s]-row[27+s]
                out[2+s]=excess;out[4+s]=storage;out[7+s]=exchange;out[9+s]=work[i][s]
                out[11+s]=storage+exchange-net;out[14+s]=tau;out[16+s]=retained;out[18+s]=drive
                scale[s]=V*(row[3+s]+row[s])+abs(particles[i][s])+abs(row[27+s])
                # A tiny nonzero excess has its own relative scale; it must not
                # pass on the absolute device-energy budget if replaced by zero.
                scale[2+s]=retained*energy_scale/V
                scale[7+s]=lost*energy_scale
                scale[14+s]=tau;scale[16+s]=retained;scale[18+s]=energy_scale/V
            out[13]=out[6]-out[7]-out[8]+heat[i]-row[31]+row[32]+row[33]
            for k in (4,5,6,9,10,11,12,13):scale[k]=energy_scale
            reference.append(out);scales.append(scale)
        failures=[]
        expected_keys={'scope','cells','heat_flux_W','device_state_advanced','complete_device_energy',
                       'physical_validated','nonlinear_face_coupling_solved'}
        if not isinstance(report,dict) or set(report)!=expected_keys:raise ValueError('exact local report coverage required')
        if report['scope']!=SCOPE or any(report[k] is not False for k in expected_keys-{'scope','cells','heat_flux_W'}):
            failures.append('scope')
        if not isinstance(report['cells'],list) or len(report['cells'])!=nc or len(report['heat_flux_W'])!=nf:
            raise ValueError('exact cell/face report coverage required')
        for i,(out,scale,given) in enumerate(zip(reference,scales,report['cells'])):
            if not isinstance(given,dict) or set(given)!=set(FIELDS):raise ValueError('exact cell field coverage required')
            for k,key in enumerate(FIELDS):
                if abs(number(given[key])-out[k])>rt*max(abs(out[k]),scale[k]):failures.append(f'cell {i} {key}')
        for i,(given,ref) in enumerate(zip(report['heat_flux_W'],fourier)):
            if abs(number(given)-ref)>rt*abs(ref):failures.append(f'face {i}')
        particle_max=max(abs(row[s]) for row in reference for s in (0,1))
        energy_max=max(abs(row[s]) for row in reference for s in (11,12,13))
        return dict(valid=not failures,failures=failures,prescribed_moments_verified=not failures,
            local_residuals_closed=not failures and particle_max<=pa and energy_max<=ea,
            max_particle_residual=str(particle_max),max_energy_residual_J=str(energy_max),
            reference_cells=[dict(zip(FIELDS,map(str,row))) for row in reference],
            reference_heat_flux_W=list(map(str,fourier)),
            device_state_advanced=False,complete_device_energy=False,physical_validated=False,
            nonlinear_face_coupling_solved=False)
