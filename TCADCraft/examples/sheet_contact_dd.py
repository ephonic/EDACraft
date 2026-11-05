"""Finite edge contact resistance on an ideal sheet FET; SI, uncalibrated."""
import json
import numpy as np
from tcad.material import graphene_sheet,mos2_sheet
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion


def main():
    x=np.linspace(0,200e-9,17);y=np.linspace(0,100e-9,3)
    z=np.linspace(-16e-9,16e-9,9)
    for material in (graphene_sheet(),mos2_sheet(reference_eV=-.9)):
        st=material.statistics()
        for resistance in (.001,.003,.01):
            sim=DielectricSheetDriftDiffusion(x,y,z,material,sheet_index=4,permittivity_F_m=3.9*8.8541878128e-12,
                mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,doping_m2=float(st.n_m2-st.p_m2),
                transport_scheme='diffusion_enhanced',contact_resistance_ohm_m=resistance)
            r=sim.solve(top_gate_voltage_V=-.1,drain_voltage_V=.02,max_iter=120,tolerance=1e-12)
            if not r['converged']:raise RuntimeError(r['status'])
            print(json.dumps(dict(material=material.name,contact_resistance_ohm_m=resistance,
                drain_current_A=r['terminal_currents_into_sheet_A']['drain'],
                contact_dissipation_W=r['contact_dissipation_W'],sheet_dissipation_W=r['sheet_dissipation_W'],
                power_defect_W=r['terminal_power_W']-r['dissipation_W'],parameters='representative, not calibrated')))

if __name__=='__main__':main()
