"""Backward-Euler isothermal sheet DD with owned, transactional history.

This advances carrier storage, with electrostatics solved at the new drive.
Optional single-level traps include four-rate capture/emission kinetics.
Terminal displacement currents are differences of electrode charge reactions;
conduction currents alone do not satisfy zero-sum KCL during charging.
"""
import copy

import numpy as np

from tcad.material.sheet import Q, _positive_scalar, _finite
from .sheet_drift_diffusion import SheetDriftDiffusion
from .sheet_dielectric import DielectricSheetDriftDiffusion
from .sheet_traps import SheetTrap
from .sheet_trap_balance import EnergySheetTrap


class SheetTransient:
    """Small-mesh fixed-step BE integrator, initialized by a converged DC solve.

    ``initial_drive`` is a dictionary of the device's solve voltage arguments.
    ``step(dt_s=..., **drive)`` replaces selected voltages, keeping the rest.
    The common Fermi energy reference is fixed for the lifetime of the driver.
    Only a fully built converged result commits; failures retain the accepted
    state/time/drive. Returned arrays are independent copies. No automatic
    time-step control or cross-process restart is provided.
    """
    def __init__(self,device,*,initial_drive,max_iter=80,tolerance=1e-10,
                 traps=None,initial_occupancy=None):
        if type(device) not in (SheetDriftDiffusion,DielectricSheetDriftDiffusion):
            raise TypeError('device must be a supported sheet DD solver')
        # SuperLU is immutable after construction, but cannot be pickled.
        # Own every mutable Python array/map; share only its read-only factor.
        factor=getattr(getattr(device,'dielectric',None),'_factor',None)
        self._device=copy.deepcopy(device,{id(factor):factor} if factor is not None else {})
        equilibrium=isinstance(initial_occupancy,str) and initial_occupancy=='equilibrium'
        if equilibrium and type(traps) is not EnergySheetTrap:
            raise ValueError('equilibrium initialization requires EnergySheetTrap')
        if traps is not None:
            if type(traps) not in (SheetTrap,EnergySheetTrap):raise TypeError('traps must be a SheetTrap or EnergySheetTrap')
            if initial_occupancy is None:raise ValueError('initial_occupancy is required for traps')
            model=traps.bind(self._device.shape)
            occupancy=None if equilibrium else self._device._field(initial_occupancy,'initial_occupancy')
            if not equilibrium and (np.any(occupancy<0) or np.any(occupancy>1)):
                raise ValueError('initial_occupancy must be in [0,1]')
            self._device._sheet_trap=(model,occupancy,None)
        elif initial_occupancy is not None:
            raise ValueError('initial_occupancy requires traps')
        self._allowed={'source_voltage_V','drain_voltage_V'}
        if type(device) is DielectricSheetDriftDiffusion:
            self._allowed.update(('top_gate_voltage_V','bottom_gate_voltage_V'))
            required='top_gate_voltage_V'
        else:
            self._allowed.add('gate_voltage_V');required='gate_voltage_V'
        if not isinstance(initial_drive,dict) or required not in initial_drive:
            raise ValueError('initial_drive must contain '+required)
        if set(initial_drive)-self._allowed-{'fermi_offset_eV'}:
            raise ValueError('initial_drive contains unsupported arguments')
        drive=copy.deepcopy(initial_drive)
        if equilibrium:
            voltages=[]
            for name in ('source_voltage_V','drain_voltage_V','fermi_offset_eV'):
                value=_finite(drive.get(name,0.),name)
                if value.ndim:raise ValueError(name+' must be scalar')
                voltages.append(float(value))
            source,drain,offset=voltages
            if source!=drain:
                raise ValueError('thermal equilibrium requires equal source and drain voltages')
            common=offset-source
            if not np.isfinite(common):raise ValueError('equilibrium Fermi energy must be finite')
            self._device._sheet_equilibrium_fermi_eV=common
        result=self._device.solve(**drive,max_iter=max_iter,tolerance=tolerance)
        if not result['converged']:
            raise ValueError('initial DC solve did not converge: '+result['status'])
        result.update(time_s=0.,accepted=True,time_scheme='backward_euler')
        if equilibrium:
            # Commit the converged occupancy as history, then remove the
            # initialization constraint. Subsequent steps must evolve f.
            self._device._sheet_trap=(model,result['trap_occupancy'].ravel().copy(),None)
            del self._device._sheet_equilibrium_fermi_eV
            result.update(trap_initialization='thermal_equilibrium',trap_equilibrium_fermi_eV=common)
        self._state=copy.deepcopy(result);self._drive=drive;self._time=0.

    @property
    def time_s(self):
        return self._time

    @property
    def state(self):
        return copy.deepcopy(self._state)

    def clear_linear_cache(self):
        """Release this driver's optional Newton preconditioner between steps.

        Return whether a cached factor was released. Accepted state, time and
        drive are unchanged; the next linear solve rebuilds its preconditioner
        with the same tolerances. This can avoid retaining the DC factor while
        building the first BE factor, or an old factor when changing dt.
        Other driver copies may still share the immutable factor, and Python's
        allocator need not immediately return freed memory to the OS. The
        dielectric Schur factor is required model data and is never cleared.
        """
        if getattr(self._device,'_linear_factor',None) is None:
            return False
        self._device._linear_factor=None
        return True

    def step(self,*,dt_s,max_iter=80,tolerance=1e-10,**drive):
        dt=_positive_scalar(dt_s,'dt_s')
        if dt<1/np.finfo(float).max:
            raise ValueError('inverse dt_s must be representable in float64')
        target=self._time+dt
        if not np.isfinite(target) or target<=self._time:
            raise ValueError('new time must be finite and strictly advance')
        if set(drive)-self._allowed:
            raise ValueError('step accepts only gate/source/drain voltages; Fermi reference is fixed')
        next_drive=copy.deepcopy(self._drive);next_drive.update(copy.deepcopy(drive))
        previous=self._state;device=copy.copy(self._device)
        device._transient_storage=(previous['n_m2'].ravel(),previous['p_m2'].ravel(),dt)
        if hasattr(device,'_sheet_trap'):
            device._sheet_trap=(device._sheet_trap[0],previous['trap_occupancy'].ravel(),dt)
        result=device.solve(**next_drive,initial=previous,max_iter=max_iter,tolerance=tolerance)
        old_n,old_p,_=device._transient_storage
        rates=np.stack((-Q*device.area*(result['n_m2'].ravel()-old_n)/dt,
                         Q*device.area*(result['p_m2'].ravel()-old_p)/dt))
        terminal=result['terminal_currents_into_sheet_A'].copy()
        trap_rates=None
        if hasattr(device,'_sheet_trap'):
            model=device._sheet_trap[0]
            trap_rates=-Q*device.area*model.density_m2*(result['trap_occupancy'].ravel()-
                previous['trap_occupancy'].ravel())/dt
        # Ideal contacts replace continuity rows. Recover their reservoir
        # injection including the charge stored in the contact control boxes.
        if not device._has_finite_contacts:
            for name,nodes in (('source',device.left),('drain',device.right)):
                terminal[name]+=float(np.sum(rates[:,nodes]))
                if trap_rates is not None:terminal[name]+=float(np.sum(trap_rates[nodes]))
        displacement={name:(result['contact_charge_C'][name]-previous['contact_charge_C'][name])/dt
                      for name in ('source','drain')}
        gate_names=('bottom_gate','top_gate') if isinstance(device,DielectricSheetDriftDiffusion) else ('gate',)
        gate={name:(result[name+'_charge_C']-previous[name+'_charge_C'])/dt for name in gate_names}
        total={name:terminal[name]+displacement[name] for name in terminal};total.update(gate)
        source=float(next_drive.get('source_voltage_V',0.));drain=float(next_drive.get('drain_voltage_V',0.))
        charge_rate=float(np.sum(rates))
        if trap_rates is not None:
            result.update(free_carrier_charge_rate_A=charge_rate,trap_charge_rate_A=float(np.sum(trap_rates)),
                trap_charge_rate_C_s=trap_rates.reshape(device.shape).copy())
            charge_rate+=result['trap_charge_rate_A']
        result.update(terminal_currents_into_sheet_A=terminal,terminal_current_sum_A=sum(terminal.values()),
            terminal_power_W=source*terminal['source']+drain*terminal['drain'],
            carrier_charge_rate_C_s=rates.reshape((2,)+device.shape),sheet_charge_rate_A=charge_rate,
            charge_continuity_defect_A=sum(terminal.values())-charge_rate,
            contact_displacement_currents_A=displacement,gate_displacement_currents_A=gate,
            terminal_total_currents_A=total,terminal_total_current_sum_A=sum(total.values()),
            time_s=target if result['converged'] else self._time,proposed_time_s=target,dt_s=dt,
            accepted=bool(result['converged']),time_scheme='backward_euler')
        values=[*terminal.values(),*displacement.values(),*gate.values(),*total.values(),charge_rate,
                result['charge_continuity_defect_A'],result['terminal_total_current_sum_A'],result['terminal_power_W']]
        if not np.all(np.isfinite(rates)) or not np.all(np.isfinite(values)):
            raise FloatingPointError('transient charge/current ledger is not representable')
        # Prepare all potentially allocating public/private copies before commit.
        accepted=copy.deepcopy(result) if result['converged'] else None
        public=copy.deepcopy(result)
        if accepted is not None:
            # The shallow candidate owns any refreshed Newton factor. Publish
            # only after the ledger and both independent result copies exist.
            if hasattr(device,'_linear_factor'):
                self._device._linear_factor=device._linear_factor
            self._state=accepted;self._drive=next_drive;self._time=target
        return public
