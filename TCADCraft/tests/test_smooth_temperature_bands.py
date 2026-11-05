"""Same-material thermal band gradients must not create thermionic interfaces."""
from copy import deepcopy
import numpy as np
import pytest
from test_three_temperature import case,BUDGET
from tcad.solver.three_temperature import ThreeTemperatureElectrothermal,ThreeTemperatureState
from tcad.solver.cut_cell_transport import Q,_immutable_state_array
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy

def smooth_case(count=2,sign=-1.):
    base,old=case(count=count,uniform=True)
    model=ThreeTemperatureElectrothermal(base.mesh,permittivity_F_m=base.eps,dirichlet_V=base.bc,
        mobility_n_m2_Vs=base.mn,mobility_p_m2_Vs=base.mp,Ec_J=.56*Q,Eh_J=.56*Q,
        heat_capacity_J_m3_K=base.capacity,thermal_conductivity_W_m_K=base.conductivity,
        valleys_n=base.valleys['electrons'],valleys_p=base.valleys['holes'],
        relaxation_time_n_s=base.tau_n,relaxation_time_p_s=base.tau_p,
        band_temperature_slope_n_J_K=sign*1e-5*Q,band_temperature_slope_p_J_K=sign*2e-5*Q)
    return model,ThreeTemperatureState(old.n_m3,old.p_m3,old.trap_fraction,
        np.linspace(290.,310.,count),0.,np.linspace(350.,370.,count),np.linspace(250.,270.,count))

@pytest.mark.parametrize('count,sign',[(2,-1.),(2,1.),(4,-1.)])
def test_two_bulk_steps_with_actual_band_gradient_and_independent_energy_audit(count,sign):
    model,old=smooth_case(count,sign)
    assert not model.thermionic_faces
    for _ in range(2):
        new,report=model.step(old,2e-13,**BUDGET)
        assert audit_three_temperature_energy(model,old,new,report,**BUDGET)['valid']
        assert np.ptp(model.band_edges(new.temperature_K)[0])>0
        assert np.max(np.abs(report['cell_band_work_from_lattice_J']['electrons']))>0
        old=new

@pytest.mark.parametrize('carrier',[0,1])
def test_discontinuous_slope_requires_interface_in_both_python_and_native(carrier):
    from tcad.core._bindings import native_three_temperature_dispatch_raw
    model,old=smooth_case()
    slopes=list(model.band_temperature_slopes);s=slopes[carrier].copy();s[1]*=2
    slopes[carrier]=_immutable_state_array(s,float);model.band_temperature_slopes=tuple(slopes)
    with pytest.raises(ValueError,match='discontinuit'):model.step(old,2e-13,**BUDGET)
    args=pack_three_temperature_inputs(model,old,2e-13,**BUDGET)
    with pytest.raises(ValueError,match='discontinuit'):native_three_temperature_dispatch_raw(*args,600)

def test_reference_band_jump_still_rejected_without_interface():
    from tcad.core._bindings import native_three_temperature_dispatch_raw
    model,old=smooth_case();args=list(pack_three_temperature_inputs(model,old,2e-13,**BUDGET))
    cells=list(args[0]);cells[21+13]=str(float(cells[21+13])+.01*Q);args[0]=cells
    with pytest.raises(ValueError,match='discontinuit'):native_three_temperature_dispatch_raw(*args,600)
