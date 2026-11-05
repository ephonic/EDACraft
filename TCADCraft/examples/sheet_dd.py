"""Run a representative ideal-sheet low-field transfer sweep (SI units)."""
import json
import numpy as np
from tcad.material import graphene_sheet,mos2_sheet
from tcad.solver.sheet_drift_diffusion import SheetDriftDiffusion


def main():
    for material in (graphene_sheet(),mos2_sheet(reference_eV=-.9)):
        x=np.linspace(0.,1e-6,21);y=np.linspace(0.,2e-6,5)
        seed=material.statistics()
        solver=SheetDriftDiffusion(x,y,material,gate_capacitance_F_m2=.02,
            mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,sheet_permittivity_F=4e-20,
            doping_m2=float(seed.n_m2-seed.p_m2))
        previous=None
        for gate in (-.1,0.,.1):
            result=solver.solve(gate_voltage_V=gate,drain_voltage_V=.02,initial=previous)
            if not result['converged']:raise RuntimeError(result['status'])
            previous=result
            print(json.dumps(dict(material=material.name,gate_V=gate,drain_V=.02,
                drain_current_A=result['terminal_currents_into_sheet_A']['drain'],
                residual=result['residual_scaled_linf'],KCL_A=result['terminal_current_sum_A'],
                model=result['model'],parameters='representative, not calibrated')))


if __name__=='__main__':main()
