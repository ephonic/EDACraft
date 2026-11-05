"""SI cut-cell kernels and classical charge compatibility are separate contracts."""
import json
import os
import numpy as np
import pytest
from tcad.core import native_constants
from tcad.physics.native_spectral import native_spectral_face
from tcad.postprocess.fermi_spectral_energy import audit_fermi_spectral_energy
from test_native_spectral import arguments
from test_fermi_spectral import fixture,BUDGET,VALLEYS
from test_transport_parameter_guard import resistor
from test_ii_field_floor import thin_result


# Stage 362 intentionally corrects the simultaneous HFS/II source current.
# Those two old numerical snapshots are replaced by independent generation,
# residual and Jacobian controls in test_hfs_ii_current.py. Charge compatibility
# still freezes every classical combination whose equations are unchanged.
# Stage 366 also replaces the old failed classical II Newton snapshot with
# independently checked converged states in test_ii_newton_merit.py.
CLASSICAL_CASES=[(newton,hfs,ii) for newton in [False,True] for hfs in [False,True]
                 for ii in [False,True] if not (hfs and ii) and not (newton and ii)]
FACE_CASES=[(mode,sign) for mode in ['endpoint_barrier','linear_series','thermionic'] for sign in [-1,1]]
COUPLED_CASES=[(dispatch,bias) for dispatch in ['python','native'] for bias in [-.002,.002]]


def classical_case(newton,hfs,ii):
    _,sim=resistor();sim.set_use_newton(newton);sim.set_newton_primary(newton)
    sim.set_high_field_saturation(hfs,5e4,4e4,2.,1.,1)
    sim.set_ii_params(10.,0.,20.,0.);sim.set_ii_enabled(ii)
    return thin_result(sim.solve())


def face_case(mode,sign):
    one,two,kwargs=arguments(2. if mode=='thermionic' else None)
    kwargs['charge_sign']=sign
    if mode!='thermionic':kwargs['bulk_potential_path']=mode
    return native_spectral_face(one,two,VALLEYS,**kwargs)


def coupled_case(dispatch,bias):
    model,state=fixture(contacts=True,density_scale=10.,voltage=bias)
    model.spectral_backend=model.local_backend=model.poisson_backend=model.nonlinear_backend='native'
    model.residual_backend=dispatch
    snapshots=[]
    for _ in range(2):
        old=state;state,report=model.step(old,2e-13,**BUDGET)
        audit=audit_fermi_spectral_energy(model,old,state,report,**BUDGET)
        assert audit['valid'],audit
        snapshots.append(dict(n=[str(v) for v in state.n_m3],p=[str(v) for v in state.p_m3],
            temperature=state.temperature_K.tolist(),time=state.time_s))
    return snapshots


def oracle():
    with open(os.environ['TCAD_SI_TRANSPORT_ORACLE'],encoding='utf8') as f:return json.load(f)


def test_charge_contracts_are_reported_separately(monkeypatch):
    info=native_constants()
    assert info['standalone_transport_scope']=='SI_cut_cell_spectral'
    assert info['standalone_elementary_charge_C']==1.602176634e-19
    assert info['standalone_elementary_charge_definition_C']=='1.602176634e-19'
    expected=1.602192e-19 if info['profile']=='legacy-charge' else 1.602176634e-19
    assert float(info['elementary_charge_C'])==expected
    monkeypatch.setenv('TCAD_CONSTANTS_PROFILE','si' if info['profile']=='legacy-charge' else 'legacy-charge')
    assert native_constants()==info


@pytest.mark.parametrize('newton,hfs,ii',CLASSICAL_CASES)
def test_classical_results_exactly_preserve_parent(newton,hfs,ii):
    key=str((newton,hfs,ii))
    assert classical_case(newton,hfs,ii)==oracle()['classical'][native_constants()['profile']][key]


@pytest.mark.parametrize('mode,sign',FACE_CASES)
def test_same_physical_face_exactly_preserves_frozen_SI(mode,sign):
    assert face_case(mode,sign)==oracle()['faces'][str((mode,sign))]


@pytest.mark.parametrize('dispatch,bias',COUPLED_CASES)
def test_same_coupled_inputs_preserve_frozen_SI_and_independent_audit(dispatch,bias):
    assert coupled_case(dispatch,bias)==oracle()['coupled'][str((dispatch,bias))]
