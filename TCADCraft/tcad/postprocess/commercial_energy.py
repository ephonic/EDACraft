"""Audits of Sentaurus thermode heat-flux exports.

Sentaurus reports ``lHeatFlux`` in W for 3-D, W/um for 2-D, and W/um2 for
1-D.  The sign at a thermode is the flux entering the device, so the outward
lattice heat power is the negative sum of the thermode values after the
dimensional conversion.  This audit intentionally keeps lattice heat separate
from carrier energy flux: a Thermodynamic deck does not export eHeatFlux and
hHeatFlux, so their absence cannot be silently treated as zero.
"""
import math
from collections.abc import Mapping
from pathlib import Path
import re


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite real scalar')
    return float(value)


def audit_sentaurus_thermode_flux(*, left_lheatflux, right_lheatflux,
                                  left_voltage_V, right_voltage_V,
                                  right_current_A, left_current_A=None,
                                  dimension='2d', depth_um=1., area_um2=1.,
                                  relative_gate=0.1, power_floor_W=1e-30):
    """Return a signed commercial lattice-heat audit in SI watts.

    ``depth_um`` is the out-of-plane width for a 2-D export.  For a 1-D
    export, ``area_um2`` is the cross-sectional area.  The electrical power is
    the right terminal current times the right-minus-left voltage.  The result
    reports a lattice-only gate and keeps ``complete_energy_closure=False``
    unless carrier heat fluxes are explicitly supplied by a separate audit.
    """
    left=_finite(left_lheatflux,'left_lheatflux');right=_finite(right_lheatflux,'right_lheatflux')
    vl=_finite(left_voltage_V,'left_voltage_V');vr=_finite(right_voltage_V,'right_voltage_V')
    current=_finite(right_current_A,'right_current_A')
    if left_current_A is not None:
        il=_finite(left_current_A,'left_current_A')
        current_balance=il+current
    else:
        current_balance=0.
    if dimension not in ('1d','2d','3d'):raise ValueError('dimension must be 1d, 2d or 3d')
    if dimension=='2d':
        width=_finite(depth_um,'depth_um')
        if width<=0:raise ValueError('depth_um must be positive')
        scale=width
        unit='W/um'
    elif dimension=='1d':
        width=_finite(area_um2,'area_um2')
        if width<=0:raise ValueError('area_um2 must be positive')
        scale=width
        unit='W/um2'
    else:
        scale=1.;unit='W'
    gate=_finite(relative_gate,'relative_gate')
    if gate<0:raise ValueError('relative_gate must be nonnegative')
    floor=_finite(power_floor_W,'power_floor_W')
    if floor<=0:raise ValueError('power_floor_W must be positive')
    outward_heat=-(left+right)*scale
    electrical=(vr-vl)*current
    residual=electrical-outward_heat
    relative=abs(residual)/max(abs(electrical),floor)
    return dict(valid=bool(relative<=gate),dimension=dimension,source_unit=unit,
        conversion_scale=scale,left_lattice_heat_flux=left,right_lattice_heat_flux=right,
        outward_lattice_heat_power_W=outward_heat,electrical_power_W=electrical,
        lattice_power_residual_W=residual,lattice_power_relative_error=relative,
        terminal_current_balance_A=current_balance,terminal_current_balance_valid=abs(current_balance)<=1e-12,
        lattice_flux_gate_relative=gate,carrier_energy_flux_exported=False,
        complete_energy_closure=False,physical_validated=False)


def read_sentaurus_plt_rows(path):
    """Read complete DF-ISE xyplot rows; reject partial or ambiguous exports.

    Values retain their exported units. No final state or completed sweep is
    inferred from the presence of a row; check the simulator exit and endpoint.
    """
    text=Path(path).read_text(encoding='utf-8')
    if not text.startswith('DF-ISE text'):
        raise ValueError('expected a text DF-ISE export')
    datasets=re.findall(r'datasets\s*=\s*\[([^\]]*)\]',text,re.S)
    blocks=re.findall(r'\bData\s*\{([^{}]*)\}\s*$',text,re.S)
    if len(datasets)!=1 or len(blocks)!=1 or len(re.findall(r'\bData\s*\{',text))!=1:
        raise ValueError('one dataset list and one complete Data block required')
    names=re.findall(r'"([^"\n]+)"',datasets[0])
    if not names or len(set(names))!=len(names) or re.sub(r'"[^"\n]+"','',datasets[0]).strip():
        raise ValueError('nonempty unique quoted dataset names required')
    try:
        values=[float(token.replace('D','E').replace('d','e')) for token in blocks[0].split()]
    except ValueError as exc:
        raise ValueError('invalid numeric DF-ISE data') from exc
    if not values or len(values)%len(names) or not all(math.isfinite(v) for v in values):
        raise ValueError('finite complete nonempty DF-ISE rows required')
    return [dict(zip(names,values[start:start+len(names)])) for start in range(0,len(values),len(names))]


def audit_sentaurus_hydrodynamic_flux(values, *, electrodes, thermodes,
                                      power_atol_W, current_atol_A,
                                      dimension='2d', depth_um=1., area_um2=1.,
                                      current_unit='per_dimension',
                                      power_rtol=1e-3, current_rtol=1e-8,
                                      reference_voltage_V=None):
    """Audit signed steady electrical/lattice/electron/hole terminal powers.

    ``values`` is one DF-ISE row. Every specified thermode must explicitly
    export lHeatFlux, eHeatFlux and hHeatFlux (positive into the device).
    Voltages are in V. Raw currents/heat powers are A/W for 3-D, A/um and
    W/um for 2-D, or A/um2 and W/um2 for 1-D. Set current_unit='A' only
    for currents already integrated over the specified extrusion. A deck's
    AreaFactor must be accounted for by the caller; it is never inferred.

    The caller lists all active ports. This checks a modeled steady terminal
    balance, not transient storage, arbitrary material band-work terms, or
    physical validation. The electrical power uses an explicit voltage
    reference and KCL is a separate mandatory gate.
    """
    if not isinstance(values,Mapping): raise ValueError('values must be a dataset mapping')
    def ports(items,name):
        if isinstance(items,(str,bytes)):
            raise ValueError(name+' must be a sequence of distinct port names')
        try: result=tuple(items)
        except TypeError as exc: raise ValueError(name+' must contain port names') from exc
        if (not result or any(not isinstance(p,str) or not p.strip() for p in result)
                or len(set(result))!=len(result)):
            raise ValueError(name+' must contain nonempty distinct port names')
        return result
    electrical_ports=ports(electrodes,'electrodes'); thermal_ports=ports(thermodes,'thermodes')
    if dimension not in ('1d','2d','3d'): raise ValueError('dimension must be 1d, 2d or 3d')
    if current_unit not in ('per_dimension','A'): raise ValueError('current_unit must be per_dimension or A')
    scale=1.
    if dimension!='3d':
        scale=_finite(depth_um if dimension=='2d' else area_um2,'extrusion')
        if scale<=0: raise ValueError('positive extrusion required')
    budgets={name:_finite(value,name) for name,value in
             [('power_atol_W',power_atol_W),('current_atol_A',current_atol_A),
              ('power_rtol',power_rtol),('current_rtol',current_rtol)]}
    if any(v<0 for v in budgets.values()): raise ValueError('nonnegative error budgets required')
    def scalar(name):
        if name not in values: raise ValueError('missing exported dataset: '+name)
        return _finite(values[name],name)
    def finite_sum(items,name):
        try: value=math.fsum(items)
        except (OverflowError,ValueError) as exc: raise ValueError(name+' overflow') from exc
        return _finite(value,name)
    voltage={p:scalar(p+' OuterVoltage') for p in electrical_ports}
    currents={p:_finite(scalar(p+' TotalCurrent')*(scale if current_unit=='per_dimension' else 1.),p+' current_A')
              for p in electrical_ports}
    reference=(voltage[electrical_ports[0]] if reference_voltage_V is None else
               _finite(reference_voltage_V,'reference_voltage_V'))
    electrical=finite_sum(((voltage[p]-reference)*currents[p] for p in electrical_ports),'electrical power')
    current_balance=finite_sum(currents.values(),'current balance')
    current_budget=_finite(budgets['current_atol_A']+budgets['current_rtol']*max(map(abs,currents.values())),'current budget')
    heat={}
    for name in ('lHeatFlux','eHeatFlux','hHeatFlux'):
        heat[name]={p:_finite(-scale*scalar(p+' '+name),p+' outward '+name) for p in thermal_ports}
    components={name:finite_sum(heat[name].values(),name+' total') for name in heat}
    outward=finite_sum(components.values(),'outward heat power')
    residual=_finite(electrical-outward,'power residual')
    power_budget=_finite(budgets['power_atol_W']+budgets['power_rtol']*max(abs(electrical),abs(outward)),'power budget')
    kcl=abs(current_balance)<=current_budget
    power_ok=abs(residual)<=power_budget
    return dict(valid=bool(kcl and power_ok),modeled_steady_terminal_balance_validated=bool(kcl and power_ok),
        dimension=dimension,source_heat_unit={'1d':'W/um2','2d':'W/um','3d':'W'}[dimension],
        extrusion_scale=scale,current_unit=current_unit,reference_voltage_V=reference,
        electrode_currents_A=currents,terminal_current_balance_A=current_balance,
        terminal_current_balance_valid=bool(kcl),current_error_budget_A=current_budget,
        electrical_power_W=electrical,outward_heat_power_W=outward,
        outward_lattice_heat_power_W=components['lHeatFlux'],
        outward_electron_heat_power_W=components['eHeatFlux'],outward_hole_heat_power_W=components['hHeatFlux'],
        thermode_outward_heat_W=heat,power_residual_W=residual,power_error_budget_W=power_budget,
        power_balance_valid=bool(power_ok),carrier_energy_flux_exported=True,
        complete_energy_closure=False,complete_device_energy=False,physical_validated=False)


def audit_sentaurus_contact_energy_flux(values, *, contact_band_edges_eV,
                                        electrodes, thermodes,
                                        power_atol_W, current_atol_A,
                                        dimension='2d', depth_um=1., area_um2=1.,
                                        current_unit='per_dimension',
                                        power_rtol=1e-3, current_rtol=1e-8,
                                        reference_voltage_V=None, reference_energy_eV=None):
    """Check steady kinetic heat flux against independently supplied band work.

    Each electrical port supplies actual contact band energies in eV as
    ``{'conduction': Ec, 'valence': Ev}``, plus exported eCurrent, hCurrent,
    TotalCurrent and DisplacementCurrent in ``values``. Currents are positive
    into the device. The energy drive is -sum(Ec*In + Ev*Ip); using eV and A
    directly gives W. One common energy reference serves both bands, so a
    recombining device retains its band-gap transfer term. Current components,
    negligible steady displacement and total KCL are separate required gates.

    Sentaurus eHeatFlux/hHeatFlux are kinetic-energy fluxes. At unequal bath
    temperatures their sum with lattice heat need not equal applied V*I:
    contact band work also includes the reservoir/material contribution.
    Both balances are reported. No correction is fitted to the heat flux.
    The caller must supply actual band values at every current-carrying
    contact and account for any additional sources/boundaries separately.
    This is a steady boundary audit, not complete device energy validation.
    """
    if isinstance(electrodes,(str,bytes)):
        raise ValueError('electrodes must be a sequence of distinct port names')
    try: ports=tuple(electrodes)
    except TypeError as exc: raise ValueError('electrodes must contain port names') from exc
    result=audit_sentaurus_hydrodynamic_flux(values,electrodes=ports,thermodes=thermodes,
        power_atol_W=power_atol_W,current_atol_A=current_atol_A,
        dimension=dimension,depth_um=depth_um,area_um2=area_um2,current_unit=current_unit,
        power_rtol=power_rtol,current_rtol=current_rtol,reference_voltage_V=reference_voltage_V)
    if not isinstance(contact_band_edges_eV,Mapping) or set(contact_band_edges_eV)!=set(ports):
        raise ValueError('contact band energies must cover exactly the electrical ports')
    bands={}
    for port in ports:
        entry=contact_band_edges_eV[port]
        if not isinstance(entry,Mapping) or set(entry)!={'conduction','valence'}:
            raise ValueError('each contact must supply conduction and valence energies in eV')
        bands[port]={key:_finite(entry[key],port+' '+key+' eV') for key in entry}
        if bands[port]['conduction']<bands[port]['valence']:
            raise ValueError('contact conduction edge must not be below valence edge')
    reference=bands[ports[0]]['conduction'] if reference_energy_eV is None else _finite(reference_energy_eV,'reference_energy_eV')
    scale=result['extrusion_scale'] if current_unit=='per_dimension' else 1.
    def scalar(key):
        if key not in values: raise ValueError('missing exported dataset: '+key)
        return _finite(values[key],key)
    def total(items,name):
        try: value=math.fsum(items)
        except (ValueError,OverflowError) as exc: raise ValueError(name+' overflow') from exc
        return _finite(value,name)
    currents={port:{key:_finite(scale*scalar(port+' '+dataset),port+' '+key+' current_A')
        for key,dataset in [('electron','eCurrent'),('hole','hCurrent'),('displacement','DisplacementCurrent')]}
        for port in ports}
    mismatch={port:total([*currents[port].values(),-result['electrode_currents_A'][port]],port+' component residual')
              for port in ports}
    budget=result['current_error_budget_A']
    composition_ok=all(abs(v)<=budget for v in mismatch.values())
    stationary=all(abs(currents[p]['displacement'])<=budget for p in ports)
    work=total((-(bands[p][band]-reference)*currents[p][carrier] for p in ports
                for band,carrier in [('conduction','electron'),('valence','hole')]),'contact band work')
    residual=_finite(work-result['outward_heat_power_W'],'contact energy residual')
    power_budget=_finite(power_atol_W+power_rtol*max(abs(work),abs(result['outward_heat_power_W'])),'contact power budget')
    power_ok=abs(residual)<=power_budget
    valid=bool(result['terminal_current_balance_valid'] and composition_ok and stationary and power_ok)
    result.update(electrical_only_balance_valid=result['valid'],
        electrical_only_power_residual_W=result['power_residual_W'],
        electrical_only_power_error_budget_W=result['power_error_budget_W'],
        valid=valid,modeled_steady_terminal_balance_validated=valid,
        energy_accounting='steady_kinetic_flux_and_contact_band_work',
        contact_band_edges_eV=bands,reference_energy_eV=reference,
        electrode_component_currents_A=currents,current_component_residuals_A=mismatch,
        current_components_valid=bool(composition_ok),steady_displacement_valid=bool(stationary),
        contact_band_work_W=work,
        contact_material_work_W=_finite(work-result['electrical_power_W'],'contact material work'),
        power_residual_W=residual,power_error_budget_W=power_budget,power_balance_valid=bool(power_ok))
    return result
