"""Independent80-digit Decimal reconstruction of a discrete collision table.

No imports from the production source or its native geometry/FD kernels.
This verifies a supplied table, not its continuum convergence or material fit.
"""
from decimal import Decimal,localcontext
import math
import numpy as np

def reference_auger_source(state,events):
    events=tuple(events)
    if not 1<=len(events)<=4096:raise ValueError('reference requires1..4096 collision events')
    with localcontext() as ctx:
        ctx.prec=80
        def D(x):return Decimal(np.format_float_scientific(np.longdouble(x),precision=35,unique=False))
        kb=Decimal('1.380649e-23');m0=Decimal('9.1093837015e-31')
        hbar=Decimal('6.62607015e-34')/(2*Decimal('3.141592653589793238462643383279502884197169399375105820974944592307816406286'))
        tn,tp,mun,mup,ec,eh,mn,mp=[D(getattr(state,n)) for n in ('temperature_n_K','temperature_p_K','mu_n_J','mu_p_J','Ec_J','Eh_J','mass_n_ratio','mass_p_ratio')]
        if min(tn,tp,mn,mp,ec+eh)<=0:raise ValueError('invalid reference state')
        def logf(z):return -(1+(-z).exp()).ln() if z>=0 else z-(1+z.exp()).ln()
        result=dict(auger_rate_m3_s=Decimal(0),impact_rate_m3_s=Decimal(0),net_recombination_rate_m3_s=Decimal(0),
            eeh_net_rate_m3_s=Decimal(0),hhe_net_rate_m3_s=Decimal(0),electron_number_source_m3_s=Decimal(0),hole_number_source_m3_s=Decimal(0),
            electron_energy_source_W_m3=Decimal(0),hole_energy_source_W_m3=Decimal(0),lattice_heat_W_m3=Decimal(0),total_charge_source_C_m3_s=Decimal(0),
            total_energy_source_W_m3=Decimal(0),entropy_production_W_m3_K=Decimal(0),maximum_kinematic_scaled_defect=Decimal(0))
        rows=[]
        for event in events:
            hole=event.channel=='hhe';mass=mp if hole else mn;other=mn if hole else mp
            edge=eh if hole else ec;minor=ec if hole else eh;mu=mup if hole else mun;muo=mun if hole else mup
            T=tp if hole else tn;To=tn if hole else tp
            q=[[D(v) for v in row] for row in event.momentum_shape];q.append([sum(row[j] for row in q) for j in range(3)])
            norm=[sum(v*v for v in row)/(other if i==2 else mass) for i,row in enumerate(q)]
            denom=norm[3]-sum(norm[:3])
            if denom<=0:raise ValueError('reference event is kinematically forbidden')
            scale=(2*m0*(ec+eh)/denom).sqrt()/hbar
            # Recover each physical kinetic energy directly from hbar*k, also
            # for the outgoing leg: no production energy assignment is reused.
            kinetic=[sum((hbar*scale*v)**2 for v in row)/(2*m0*(other if i==2 else mass)) for i,row in enumerate(q)]
            energies=[(minor if i==2 else edge)+k for i,k in enumerate(kinetic)]
            z=[((muo if i==2 else mu)-e)/(kb*(To if i==2 else T)) for i,e in enumerate(energies)]
            la=sum(logf(-v if i==3 else v) for i,v in enumerate(z));lb=sum(logf(v if i==3 else -v) for i,v in enumerate(z))
            forward=D(event.weight_m3_s)*la.exp();reverse=D(event.weight_m3_s)*lb.exp();net=forward-reverse
            majority=(energies[3]-energies[0]-energies[1])*net;minority=-energies[2]*net
            un=minority if hole else majority;up=majority if hole else minority;sigma=kb*net*(la-lb)
            row=dict(auger_rate_m3_s=forward,impact_rate_m3_s=reverse,net_recombination_rate_m3_s=net,
                electron_energy_source_W_m3=un,hole_energy_source_W_m3=up,entropy_production_W_m3_K=sigma,
                **{f'kinetic_{i+1}_J':v for i,v in enumerate(kinetic)},wavevector_scale_m_inv=scale,
                log_forward_reverse_ratio=la-lb,on_shell_defect_J=kinetic[3]-(ec+eh)-sum(kinetic[:3]))
            rows.append({k:float(v) for k,v in row.items()})
            for k,v in [('auger_rate_m3_s',forward),('impact_rate_m3_s',reverse),('net_recombination_rate_m3_s',net),
                ('hhe_net_rate_m3_s' if hole else 'eeh_net_rate_m3_s',net),('electron_number_source_m3_s',-net),('hole_number_source_m3_s',-net),
                ('electron_energy_source_W_m3',un),('hole_energy_source_W_m3',up),('entropy_production_W_m3_K',sigma)]:result[k]+=v
        return dict({k:float(v) for k,v in result.items()},event_moments=rows)

def audit_auger_source(state,events,report,*,rtol=3e-11):
    if isinstance(rtol,(bool,np.bool_)) or not np.isscalar(rtol) or not np.isreal(rtol) or not np.isfinite(rtol) or not 0<rtol<=1e-6:
        raise ValueError('finite relative tolerance in (0,1e-6] required')
    events=tuple(events);ref=reference_auger_source(state,events);failures=[];errors={}
    gross=max(ref['auger_rate_m3_s']+ref['impact_rate_m3_s'],1e-300)
    en=max(*(abs(v) for row in ref['event_moments'] for k,v in row.items() if k.endswith('kinetic_4_J')),float(state.Ec_J+state.Eh_J),abs(float(state.Ec_J)),abs(float(state.Eh_J)))
    power=max(gross*en,1e-300);entropy=max(1.380649e-23*gross,abs(ref['entropy_production_W_m3_K']),1e-300)
    def check(label,value,expected,scale):
        if isinstance(value,(bool,np.bool_)) or not np.isscalar(value) or not np.isreal(value):failures.append(label);return
        try:value=float(value)
        except (TypeError,ValueError,OverflowError):failures.append(label);return
        if not math.isfinite(value):failures.append(label);return
        err=abs(value-expected)/max(scale,abs(expected),1e-300);errors[label]=err
        if err>rtol:failures.append(label)
    def unit(k):
        if k.endswith('W_m3_K'):return entropy
        if k.endswith('W_m3'):return power
        if k.endswith('C_m3_s'):return 1.602176634e-19*gross
        if k.endswith('m3_s'):return gross
        if k.endswith('_J'):return en
        if k=='maximum_kinematic_scaled_defect':return 1.
        return 1.
    for k,v in ref.items():
        if k!='event_moments':check(k,report.get(k),v,unit(k))
    rows=report.get('event_moments')
    if not isinstance(rows,(list,tuple)) or len(rows)!=len(events):failures.append('event_coverage')
    else:
        for i,(row,expected) in enumerate(zip(rows,ref['event_moments'])):
            if not isinstance(row,dict) or set(row)!=set(expected):failures.append(f'event{i}_fields');continue
            before=len(failures)
            for k,v in expected.items():check(f'event{i}_{k}',row.get(k),v,unit(k))
            if len(failures)==before:
                for k in ('auger_rate_m3_s','impact_rate_m3_s'):
                    if row[k]<0:failures.append(f'event{i}_{k}_negative')
                activity=max(expected['auger_rate_m3_s']+expected['impact_rate_m3_s'],1e-300)
                if row['entropy_production_W_m3_K'] < -1e-14*1.380649e-23*activity:
                    failures.append(f'event{i}_negative_entropy')
    for key,value in [('law','on_shell_parabolic_Auger_impact_event_table_v1'),('execution_backend','native'),('device_coupled',False),('material_calibrated',False),('continuum_kernel_integrated',False)]:
        wrong=report.get(key) is not value if value is False else report.get(key)!=value
        if wrong:failures.append(key)
    if not failures:
        def identity(name,value,scale):
            if abs(value)>5e-14*max(scale,1e-300):failures.append(name)
        a=report;net=a['net_recombination_rate_m3_s'];un=a['electron_energy_source_W_m3'];up=a['hole_energy_source_W_m3']
        identity('net_identity',a['auger_rate_m3_s']-a['impact_rate_m3_s']-net,gross)
        identity('particle_identity',a['electron_number_source_m3_s']+net,gross)
        identity('charge_identity',a['electron_number_source_m3_s']-a['hole_number_source_m3_s'],gross)
        identity('energy_identity',math.fsum((un,up,a['lattice_heat_W_m3'])),power)
        sigma=math.fsum(((un+float(state.mu_n_J)*net)/float(state.temperature_n_K),(up+float(state.mu_p_J)*net)/float(state.temperature_p_K)))
        identity('thermodynamic_entropy',sigma-a['entropy_production_W_m3_K'],max(entropy,power/min(float(state.temperature_n_K),float(state.temperature_p_K))))
        if a['entropy_production_W_m3_K'] < -1e-14*entropy:failures.append('negative_entropy')
        for k in ('auger_rate_m3_s','impact_rate_m3_s'):
            if a[k]<0:failures.append(k+'_negative')
        for k in ref:
            if k=='event_moments':continue
            if k=='maximum_kinematic_scaled_defect':continue
            identity('event_sum_'+k,math.fsum(row[k] for row in rows)-a[k],unit(k)) if k in rows[0] else None
    return dict(valid=not failures,failures=failures,maximum_moment_scaled_error=max(errors.values(),default=0.),reference=ref,
        relative_tolerance=float(rtol),device_coupled=False,material_calibrated=False,continuum_kernel_integrated=False,physical_validated=False)
