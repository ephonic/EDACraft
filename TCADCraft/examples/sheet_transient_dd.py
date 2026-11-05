"""Ideal, uncalibrated graphene/MoS2 pulse charging, SI units."""
import json
import numpy as np
from tcad.material import graphene_sheet, mos2_sheet
from tcad.solver.sheet_drift_diffusion import SheetDriftDiffusion
from tcad.solver.sheet_transient import SheetTransient


def main():
    for name,material in (('graphene',graphene_sheet()),('mos2',mos2_sheet(reference_eV=-.9))):
        sim=SheetDriftDiffusion(np.linspace(0,200e-9,9),np.linspace(0,100e-9,3),material,
            gate_capacitance_F_m2=.006,mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,
            transport_scheme='diffusion_enhanced',contact_resistance_ohm_m=.003)
        tr=SheetTransient(sim,initial_drive={'gate_voltage_V':0.},max_iter=120)
        for vg in (.02,.02,0.,0.):
            r=tr.step(dt_s=2e-12,gate_voltage_V=vg,max_iter=120,tolerance=1e-12)
            assert r['accepted']
            print(json.dumps(dict(material=name,time_s=r['time_s'],sheet_charge_C=r['sheet_charge_C'],
                conduction_sum_A=r['terminal_current_sum_A'],terminal_total_currents_A=r['terminal_total_currents_A'],
                total_KCL_A=r['terminal_total_current_sum_A'])))


if __name__=='__main__':main()
