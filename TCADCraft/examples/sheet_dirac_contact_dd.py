"""Uncalibrated gapless graphene finite Dirac edge mode supply."""
import json
import numpy as np
from tcad.material import graphene_sheet
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion


def main():
    x=np.linspace(0,200e-9,17);y=np.linspace(0,100e-9,3);z=np.linspace(-16e-9,16e-9,9)
    for offset in (0.,-.1,.1):
        sim=DielectricSheetDriftDiffusion(x,y,z,graphene_sheet(),sheet_index=4,permittivity_F_m=3.9*8.8541878128e-12,
            mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,transport_scheme='diffusion_enhanced',dirac_contact_offset_eV=offset)
        for bias in (-.02,.02):
            r=sim.solve(top_gate_voltage_V=-.1,drain_voltage_V=bias,max_iter=120,tolerance=1e-12)
            if not r['converged']:raise RuntimeError(r['status'])
            print(json.dumps(dict(material='Graphene sheet',dirac_contact_offset_eV=offset,drain_V=bias,
                current_A=r['terminal_currents_into_sheet_A']['drain'],contact_dissipation_W=r['contact_dissipation_W'],
                power_defect_W=r['terminal_power_W']-r['dissipation_W'],parameters='ideal mode supply, not calibrated')))

if __name__=='__main__':main()
