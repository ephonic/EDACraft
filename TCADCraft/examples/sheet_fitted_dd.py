"""Diffusion-enhanced SG transfer sweep with explicitly meshed dielectric."""
import json
import numpy as np
from tcad.material import graphene_sheet,mos2_sheet
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion

def main():
    x=(.5-.5*np.cos(np.linspace(0,np.pi,33)))*200e-9;y=np.linspace(0,100e-9,3)
    z=np.linspace(-16e-9,16e-9,9);eps=np.r_[np.full(4,3.9),np.full(4,9.)][:,None,None]*8.8541878128e-12
    for material in (graphene_sheet(),mos2_sheet(reference_eV=-.9)):
        seed=material.statistics()
        sim=DielectricSheetDriftDiffusion(x,y,z,material,sheet_index=4,permittivity_F_m=eps,
            mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,doping_m2=float(seed.n_m2-seed.p_m2),
            transport_scheme='diffusion_enhanced')
        previous=None
        for gate in (-.15,0.,.15):
            result=sim.solve(top_gate_voltage_V=gate,drain_voltage_V=.02,initial=previous,max_iter=120)
            if not result['converged']:raise RuntimeError(result['status'])
            previous=result
            print(json.dumps(dict(material=material.name,top_gate_V=gate,current_A=result['terminal_currents_into_sheet_A']['drain'],
                residual=result['residual_scaled_linf'],transport_scheme=result['transport_scheme'],
                parameters='representative, not calibrated')))

if __name__=='__main__':main()
