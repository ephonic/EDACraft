"""Illustrative energy-derived FD sheet traps; capture coefficients are uncalibrated."""
import json
import numpy as np
from tcad.material import graphene_sheet,mos2_sheet
from tcad.solver.sheet_drift_diffusion import SheetDriftDiffusion
from tcad.solver.sheet_transient import SheetTransient
from tcad.solver.sheet_trap_balance import EnergySheetTrap

for name,material in (('graphene',graphene_sheet()),('mos2',mos2_sheet(reference_eV=-.9))):
    sim=SheetDriftDiffusion(np.linspace(0,200e-9,9),np.linspace(0,100e-9,3),material,
        gate_capacitance_F_m2=.006,mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,
        contact_resistance_ohm_m=.003,transport_scheme='diffusion_enhanced')
    run=SheetTransient(sim,initial_drive={'gate_voltage_V':0.},traps=EnergySheetTrap(1e14,2e-6,1e-6,material.gap_eV/2-.04 if name=='mos2' else .01,2.),
        initial_occupancy=.2,max_iter=120,tolerance=1e-12)
    for label,voltage in (('positive_gate',.08),('zero_gate',0.),('small_gate',.01),('negative_gate',-.08)):
        r=run.step(dt_s=20e-12,gate_voltage_V=voltage,drain_voltage_V=.002 if label=='small_gate' else 0.,max_iter=120,tolerance=1e-12)
        assert r['accepted']
        print(json.dumps(dict(material=name,pulse=label,time_s=r['time_s'],mean_occupancy=float(r['trap_occupancy'].mean()),
            trap_charge_C=r['trap_charge_C'],drain_total_current_A=r['terminal_total_currents_A']['drain'],
            total_KCL_A=r['terminal_total_current_sum_A'])))
