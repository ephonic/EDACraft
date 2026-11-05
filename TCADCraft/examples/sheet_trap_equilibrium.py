"""Self-consistent thermal preparation, then a kinetic gate pulse.

Representative ideal sheet parameters; no calibrated memory window is implied.
"""
import json
import numpy as np
from tcad.material import graphene_sheet,mos2_sheet
from tcad.solver.sheet_drift_diffusion import SheetDriftDiffusion
from tcad.solver.sheet_trap_balance import EnergySheetTrap
from tcad.solver.sheet_transient import SheetTransient

for name,material in (('graphene',graphene_sheet()),('mos2',mos2_sheet(reference_eV=-.9))):
    sim=SheetDriftDiffusion(np.linspace(0,200e-9,9),np.linspace(0,100e-9,3),material,
        gate_capacitance_F_m2=.006,mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,
        contact_resistance_ohm_m=.003,transport_scheme='diffusion_enhanced')
    offset=material.gap_eV/2-.04 if name=='mos2' else .01
    model=EnergySheetTrap(1e14,2e-6,1e-6,offset,2.)
    run=SheetTransient(sim,initial_drive={'gate_voltage_V':.015},traps=model,
        initial_occupancy='equilibrium',tolerance=1e-12,max_iter=120)
    for phase,voltage in (('initial_equilibrium',None),('thermal_hold',None),('positive_pulse',.045),('negative_pulse',-.03)):
        r=run.state if phase=='initial_equilibrium' else run.step(dt_s=20e-12,
            **({} if voltage is None else {'gate_voltage_V':voltage}),tolerance=1e-12,max_iter=120)
        assert r['accepted']
        print(json.dumps(dict(material=name,phase=phase,time_s=r['time_s'],
            mean_occupancy=float(r['trap_occupancy'].mean()),trap_charge_C=r['trap_charge_C'],
            maximum_terminal_current_A=max(abs(v) for v in r['terminal_currents_into_sheet_A' if phase=='initial_equilibrium' else 'terminal_total_currents_A'].values()))))
