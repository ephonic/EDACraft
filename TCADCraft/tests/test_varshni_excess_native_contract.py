"""Native input rejection is atomic and permits a corrected configuration."""
import pytest
from test_varshni_band_excess import varshni_case,BUDGET
from tcad.solver.lattice_excess import LatticeCoupledExcessRelaxation
from tcad.core._bindings import PyDeviceSimulator


@pytest.mark.parametrize('damage',['short','negative_alpha','negative_beta','nonfinite','capacity'])
def test_invalid_native_band_configuration_leaves_session_unconfigured(damage):
    model,initial,power=varshni_case()
    cfg=LatticeCoupledExcessRelaxation(model,initial).configuration
    start=[v for c in cfg.cells for v in (*c.initial_densities_m3,c.initial_temperatures_K[2],*c.initial_temperatures_K[:2])]
    band=cfg.packed_varshni()
    if damage=='short':band=band[:-1]
    elif damage=='negative_alpha':band[0]='-1e-23'
    elif damage=='negative_beta':band[1]='-1'
    elif damage=='nonfinite':band[0]='nan'
    else:band[0]='1e-15'
    backend=PyDeviceSimulator(model.nc,1,1,1.,1.,1.)
    def configure(values):
        backend.configure_lattice_excess(start,cfg.packed_parameters(),cfg.packed_faces(),
            *cfg.cells[0].packed_valleys(),varshni=values)
    with pytest.raises(ValueError):configure(band)
    with pytest.raises((ValueError,RuntimeError)):backend.isolated_relaxation_state()
    configure(cfg.packed_varshni());before=backend.isolated_relaxation_state()
    raw,token=backend.prepare_isolated_relaxation(2e-14,**BUDGET,max_nfev=600)
    assert len(raw)>13*model.nc and backend.isolated_relaxation_state()==before
    backend.discard_isolated_relaxation(token)
    assert backend.isolated_relaxation_state()==before
