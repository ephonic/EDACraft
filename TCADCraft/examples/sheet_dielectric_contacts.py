"""Representative finite-electrode sheet pulse; not calibrated memory data."""
import json
import numpy as np

from tcad.material import graphene_sheet
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion
from tcad.solver.sheet_transient import SheetTransient
from tcad.solver.sheet_trap_balance import EnergySheetTrap

device=DielectricSheetDriftDiffusion(np.linspace(0,200e-9,7),np.linspace(0,100e-9,3),
    np.linspace(-10e-9,10e-9,9),graphene_sheet(),sheet_index=4,
    permittivity_F_m=5*8.8541878128e-12,contact_z_bounds_m=(-5e-9,5e-9),
    mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,contact_resistance_ohm_m=.003,
    transport_scheme='diffusion_enhanced')
run=SheetTransient(device,initial_drive=dict(top_gate_voltage_V=.005),
    traps=EnergySheetTrap(1e14,2e-6,1e-6,.01,1.5),initial_occupancy='equilibrium',
    tolerance=1e-12,max_iter=120)
for gate in (.025,-.01,.008):
    result=run.step(dt_s=2e-12,top_gate_voltage_V=gate,drain_voltage_V=.003,
        tolerance=1e-12,max_iter=120)
    if not result['accepted']:raise RuntimeError(result['status'])
    print(json.dumps(dict(time_s=result['time_s'],gate_V=gate,
        conduction_A=result['terminal_currents_into_sheet_A'],
        total_terminal_A=result['terminal_total_currents_A'],
        sheet_contact_charge_C=result['sheet_contact_charge_C'],
        dielectric_contact_charge_C=result['dielectric_contact_charge_C'],
        contact_charge_C=result['contact_charge_C'],gauss_charge_sum_C=result['gauss_charge_sum_C'],
        total_current_sum_A=result['terminal_total_current_sum_A'],
        scope='representative isothermal single-level trap prototype; no memory retention qualification')))
