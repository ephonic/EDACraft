"""Saved split proof, clock projection and full-interval energy audit; stdlib only."""
from dataclasses import dataclass,asdict,fields,replace
from decimal import Decimal,localcontext
import math
from tcad.postprocess.boltzmann_affine_transport import _Arithmetic,_point,_fingerprint,_metadata,ZERO
from tcad.postprocess.boltzmann_nonisothermal_transport import audit_mb_nonisothermal_transport
from tcad.postprocess.boltzmann_affine_powerlaw import audit_mb_affine_powerlaw


@dataclass(frozen=True)
class _Anchor:
    frame: tuple
    electron_excess: tuple
    hole_excess: tuple
    time_s: float
    origin_configuration_sha256: str


@dataclass(frozen=True)
class _State:
    anchor: _Anchor
    electron_density_change: tuple
    hole_density_change: tuple
    electron_energy_density_change: tuple
    hole_energy_density_change: tuple
    time_s: float


def _load(raw):
    # Separate stdlib records: replay never invokes production constructors.
    if not isinstance(raw,dict) or set(raw)!={f.name for f in fields(_State)}:raise ValueError('split saved state coverage')
    a=raw['anchor']
    if not isinstance(a,dict) or set(a)!={f.name for f in fields(_Anchor)}:raise ValueError('split saved anchor coverage')
    anchor=_Anchor(**{k:tuple(v) if k in ('frame','electron_excess','hole_excess') else v for k,v in a.items()})
    if isinstance(anchor.time_s,bool) or not math.isfinite(anchor.time_s) or anchor.time_s<0:raise ValueError('split anchor clock')
    return _State(**{k:anchor if k=='anchor' else v if k=='time_s' else tuple(v) for k,v in raw.items()})


def audit_mb_split_interval(configurations,old,new,report,*,faces,dt_s,impulses_J=None,
                            particle_atol=1e-9,energy_atol_J=1e-27,number_atol_s=1e-6,energy_atol_W=1e-15):
    with localcontext() as ctx:
        ctx.prec=10000;m=_Arithmetic();dt,pa,ea,nfa,efa=map(m.command,(dt_s,particle_atol,energy_atol_J,number_atol_s,energy_atol_W))
        n=len(old)
        if min(dt,pa,ea,nfa,efa)<=0 or not 1<=n<=256 or len(new)!=n or len(configurations)!=n:raise ValueError('split independent coverage')
        start=old[0].time_s;end=start+float(dt_s);aux=end+float(dt_s)
        if not math.isfinite(aux) or not start<end<aux or any(s.time_s!=start for s in old):raise ValueError('split physical/auxiliary clocks')
        _metadata(report,dict(scope='same_interval_Lie_split_flat_MB',execution_backend='native',precision_bits=113,
            method='transport_explicit_then_collision_BE',temporal_order=1,autonomous_operators_only=True,
            stage_clock_model='auxiliary_bookkeeping',auxiliary_collision_end_s=aux,dt_s=float(dt_s),
            physical_time_advanced=True,same_interval_split_supported=True,monolithic_coupled_BE=False,
            field_work_included=False,lattice_flux_included=False,device_statistics_selected=False,complete_device_energy=False,physical_validated=False))
        if report['physical_interval_s']!=[start,end] or report['configuration_sha256']!=[c.sha256 for c in configurations] or report['old_sha256']!=list(map(_fingerprint,old)) or report['new_sha256']!=list(map(_fingerprint,new)):
            raise ValueError('split interval/provenance mismatch')
        q=[(0.,0.,0.) for _ in old] if impulses_J is None else impulses_J
        if len(q)!=n or any(len(row)!=3 for row in q):raise ValueError('split impulse coverage')
        qd=[list(map(m.command,row)) for row in q]
        saved=report['transported_states'];collisions=report['collisions']
        if len(saved)!=n or len(collisions)!=n:raise ValueError('split stage coverage')
        middle=tuple(map(_load,saved))
        transport=audit_mb_nonisothermal_transport(old,middle,report['transport'],faces=faces,dt_s=dt_s,
            particle_atol=particle_atol,energy_atol_J=energy_atol_J/2,number_atol_s=number_atol_s,energy_atol_W=energy_atol_W)
        checks=[];valid=transport['valid'];signed=[[ZERO]*4 for _ in old];boundary=[ZERO]*4
        for spec,row in zip(faces,report['transport']['transfers']):
            for k,raw in enumerate(row['integrated']):
                value=sum(m.vector(raw),ZERO);signed[spec['owner']][k]-=value
                if 'reservoir' in spec:boundary[k]+=value
                else:signed[spec['neighbor']][k]+=value
        residuals=[ZERO]*6;budgets=[ZERO]*6;cells=[]
        for i,(cfg,a,b,mid,child) in enumerate(zip(configurations,old,new,middle,collisions)):
            if type(b.time_s) is bool or b.time_s!=end:raise ValueError('split commits one physical interval')
            projected=replace(_load(asdict(b)),time_s=aux)
            check=audit_mb_affine_powerlaw(cfg,mid,projected,child,dt_s=dt_s,impulses_J=q[i],energy_atol_J=energy_atol_J/(2*n))
            valid &= check['valid'];checks.append(check)
            before=_point(a,m);after=_point(b,m);f=before['frame'];V=f[4]
            dN=[V*(after['n'][k]-before['n'][k]) for k in range(2)]
            dU=[V*(after['K'][k]-before['K'][k]+f[k+5]*(after['n'][k]-before['n'][k])) for k in range(2)]
            dU.append(V*f[3]*(after['Tl']-before['Tl']))
            exchange=[V*sum((sum(m.vector(r['operations'][10+k]['value']),ZERO) for r in child['collision']['lineage_groups']),ZERO) for k in range(2)]
            r=[dN[k]-signed[i][k] for k in range(2)]+[dU[k]-signed[i][2+k]+exchange[k]-qd[i][k] for k in range(2)]
            r.extend((dU[2]-sum(exchange,ZERO)-qd[i][2],sum(dU,ZERO)-sum(signed[i][2:],ZERO)-sum(qd[i],ZERO)))
            tb=list(map(Decimal,transport['cells'][i]['budgets']));cb=Decimal(check['constant_coefficient_ledger_audit']['global_energy_budget_J'])
            budget=[*tb[:2],min(ea,tb[2]+cb),min(ea,tb[3]+cb),min(ea,cb),min(ea,tb[2]+tb[3]+cb)]
            passed=all(abs(x)<=y for x,y in zip(r,budget));valid &= passed
            residuals=[x+y for x,y in zip(residuals,r)];budgets=[x+y for x,y in zip(budgets,budget)]
            cells.append(dict(valid=bool(passed),residuals=[str(x) for x in r],budgets=[str(x) for x in budget]))
        budgets=[min(pa if k<2 else ea,v) for k,v in enumerate(budgets)]
        closed=all(abs(x)<=y for x,y in zip(residuals,budgets));valid &= closed
        return dict(valid=bool(valid),transport=transport,collisions=checks,cells=cells,
            row_order=['electron_particles','hole_particles','electron_energy','hole_energy','lattice_energy','total_energy'],
            global_residuals=[str(x) for x in residuals],global_budgets=[str(x) for x in budgets],
            outward_contact_transfers=[str(x) for x in boundary],whole_interval_particle_energy_closed=bool(closed),
            physical_clock_advanced_once=True,auxiliary_clock_projection_checked=True,native_physics_used=False,
            same_interval_split_supported=True,temporal_order=1,complete_device_energy=False,physical_validated=False)
