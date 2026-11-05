"""External edge ODE and calorimetric references for the thermal extension."""
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from tcad.mesh.polyhedral_regions import region_cut_cells
from tcad.solver.cut_cell_transport import CutCellState,KB,Q
from tcad.solver.electrothermal_cut_cell import ElectrothermalCutCellTransport


@pytest.mark.parametrize('left_T,right_T,drop_eV',[(300,600,0.),(600,300,.04),(250,450,-.07),(300,300,.03)])
def test_nonisothermal_SG_matches_independently_integrated_edge_ODE(left_T,right_T,drop_eV):
    # Solve the dimensional constant-number-flux edge equation with a linear
    # temperature and energy profile. No Bernoulli/log-mean formula in reference.
    mesh=region_cut_cells([np.array([0.,1e-7])]*3,{'box':[[]]})
    model=ElectrothermalCutCellTransport(mesh,permittivity_F_m=1e-10,
        dirichlet_V={0:0.},mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.01)
    start,end=1.3,.7;mu=.01;length=1e-7;area=1e-14;density=1e21
    drop=drop_eV*Q
    def endpoint(scaled_flux):
        def rhs(x,y):
            temperature=left_T+(right_T-left_T)*x
            return [-drop*y[0]/(KB*temperature)-scaled_flux/(KB*temperature)]
        return solve_ivp(rhs,(0,1),[start],rtol=2e-12,atol=2e-14).y[0,-1]
    zero=endpoint(0.);unit=endpoint(KB*300.)
    reference=(end-zero)/(unit-zero)*KB*300.*mu/Q*area/length*density
    predicted=model._edge_flux(np.array([start*density]),np.array([end*density]),
        np.array([left_T]),np.array([right_T]),np.array([0.]),np.array([drop]),
        np.ones(1),np.ones(1),np.array([mu]),np.array([mu]),np.array([area/length]))[0]
    np.testing.assert_allclose(predicted,reference,rtol=3e-11)


def test_single_cell_carrier_heat_capacity_matches_independent_calorimetry():
    length=1e-7;mesh=region_cut_cells([np.array([0.,length])]*3,{'box':[[]]})
    bath={f:350. for f in range(len(mesh.faces))}
    model=ElectrothermalCutCellTransport(mesh,permittivity_F_m=1e-10,dirichlet_V={0:0.},
        mobility_n_m2_Vs=0.,mobility_p_m2_Vs=0.,heat_capacity_J_m3_K=.1,
        thermal_conductivity_W_m_K=.001,heat_bath_K=bath)
    n=1e21;old=CutCellState(np.array([n]),np.array([n]),np.array([.5]),np.array([300.]))
    dt=2e-12;new,report=model.step(old,dt,charge_atol_C=1e-29,particle_atol=1e-12,energy_atol_J=1e-28)
    capacity=(.1+3*KB*n)*length**3
    conductance=6*.001*length**2/(length/2)
    expected=(capacity*300.+dt*conductance*350.)/(capacity+dt*conductance)
    np.testing.assert_allclose(new.temperature_K,expected,rtol=1e-13)
    np.testing.assert_allclose(sum(report['energy_increments_J'].values()),capacity*(expected-300.),rtol=1e-13)
    assert abs(report['source_work_J'])<1e-30
