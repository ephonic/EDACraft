"""Resolved weak SRH reactions must survive the single-reservoir fast path."""
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('right_reservoir',[False,True])
@pytest.mark.parametrize('lifetime',[1e-2,1e-3])
def test_weak_srh_chain_matches_independent_reaction_diffusion(axis,right_reservoir,lifetime):
    # Synthetic operator control: n=p makes symmetric SRH exactly linear,
    # R=(n-ni)/(2*tau). This is not a material calibration at high injection.
    shape=[1,1,1];shape[axis]=4
    spacing=[1.,1.,1.];spacing[axis]=1e-7
    sim=PyDeviceSimulator(*shape,*spacing)
    reservoir=3 if right_reservoir else 0;barrier=3-reservoir
    mobile=np.ones(4)*.1;mobile[barrier]=0.
    sim.set_mobility(mobile,mobile);sim.set_permittivity(np.full(4,1e-10))
    sim.set_doping(np.zeros(4));sim.set_effective_dos(np.full(4,1e19),np.full(4,1e19));sim.set_bandgap(np.zeros(4))
    sim.set_thermal_voltage(.02585);sim.set_recombination(np.full(4,lifetime),np.full(4,lifetime))
    sim.set_dirichlet_potential(dict.fromkeys(range(4),0.))
    sim.set_electron_bc({barrier:0.,reservoir:1e23});sim.set_hole_bc({barrier:0.,reservoir:1e23})
    sim.set_use_newton(False);sim.set_quantum_enabled(False);sim.set_gummel_max_iter(200);sim.set_tolerance(1e-13)
    sim.set_initial_guess(np.zeros(4),np.full(4,1e23),np.full(4,1e23))
    result=sim.solve();assert result['converged']
    diffusion=.1*.02585/1e-14;reaction=1/(2*lifetime)
    matrix=np.array([[diffusion+reaction,-diffusion],[-diffusion,2*diffusion+reaction]])
    rhs=np.array([reaction*1e19,reaction*1e19+diffusion*1e23])
    expected=np.linalg.solve(matrix,rhs)
    interior=[1,2] if right_reservoir else [2,1]
    for name in ('n','p'):np.testing.assert_allclose(result[name][interior],expected,rtol=2e-13,atol=0)
    # Independent integrated reaction/current balance is resolved even when
    # its diagonal is below the old matrix-relative fast-path audit gate.
    sign=1 if right_reservoir else -1
    rate=(expected-1e19)/(2*lifetime)
    expected_current=1.602176634e-19*np.sum(rate)*1e-7
    edge=reservoir-1 if right_reservoir else reservoir
    measured=result['Jn_'+'xyz'[axis]][edge]
    assert sign*measured==pytest.approx(expected_current,rel=2e-3,abs=1e-10)

