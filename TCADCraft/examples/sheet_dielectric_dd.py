"""Representative dual-gate sheet FET with explicitly meshed dielectric (SI)."""
import json
import numpy as np
from tcad.material import graphene_sheet,mos2_sheet
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion


def main():
    x=(.5-.5*np.cos(np.linspace(0,np.pi,17)))*200e-9;y=np.linspace(0,100e-9,3)
    z=np.array([-20.,-10.,0.,4.,8.])*1e-9
    eps=np.array([3.9,3.9,9.,9.])[:,None,None]*8.8541878128e-12
    for material in (graphene_sheet(),mos2_sheet(reference_eV=-.9)):
        stats=material.statistics()
        sim=DielectricSheetDriftDiffusion(x,y,z,material,sheet_index=2,permittivity_F_m=eps,
            mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,doping_m2=float(stats.n_m2-stats.p_m2))
        previous=None
        for gate in (-.05,0.,.05):
            result=sim.solve(top_gate_voltage_V=gate,bottom_gate_voltage_V=0.,drain_voltage_V=.02,initial=previous)
            if not result['converged']:raise RuntimeError(result['status'])
            previous=result
            print(json.dumps(dict(material=material.name,top_gate_V=gate,
                current_A=result['terminal_currents_into_sheet_A']['drain'],residual=result['residual_scaled_linf'],
                gauss_charge_sum_C=result['gauss_charge_sum_C'],model=result['model'],
                parameters='representative, not calibrated')))


if __name__=='__main__':main()
