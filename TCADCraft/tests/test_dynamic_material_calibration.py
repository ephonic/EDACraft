"""Real raw data ownership, independent drive holdout and native-law limits."""
from pathlib import Path
from dataclasses import replace
import numpy as np
import pytest
from tcad.material.dynamic_calibration import load_published_hafnia_curves,fit_switching_kinetics,switching_fraction

RAW=Path(__file__).resolve().parents[1]/'docs/validation/conservative_physics_20261017/experimental_raw/41467_2024_47194_MOESM4_ESM.xlsx'


@pytest.mark.parametrize('specimen',['LT:HfO2','La:HfO2'])
def test_real_source_traceability_and_holdout(specimen):
    curves=load_published_hafnia_curves(RAW,specimen=specimen)
    assert len(curves)==6 and all(len(c.times_s)>=20 for c in curves)
    assert curves[0].source_cells[0]==('A3','B3')
    assert curves[0].times_s[0]==4e-8
    report=fit_switching_kinetics(curves[::2],curves[1::2],rmse_budget=.10,max_error_budget=.20)
    assert report['optimizer_converged'] and report['identifiable']
    assert not report['physical_validated'] and not report['dynamic_landau_viscosity_identified']
    # Tightening the budget cannot convert the same raw holdout into a pass.
    tight=fit_switching_kinetics(curves[::2],curves[1::2],rmse_budget=1e-8,max_error_budget=1e-8)
    assert not tight['holdout_passed']
    with pytest.raises(ValueError,match='entire'):fit_switching_kinetics(curves,curves[:1],rmse_budget=.1,max_error_budget=.2)
    with pytest.raises(ValueError,match='specimens'):fit_switching_kinetics(curves[:2],[replace(curves[3],specimen='other film')],rmse_budget=.1,max_error_budget=.2)


def test_raw_source_bytes_and_labels_are_mandatory(tmp_path):
    target=tmp_path/'modified.xlsx';target.write_bytes(RAW.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='SHA256'):load_published_hafnia_curves(target,specimen='LT:HfO2')
    with pytest.raises(ValueError,match='specimen'):load_published_hafnia_curves(RAW,specimen='AlScN')


def test_native_single_time_law_and_zero_duration():
    t=np.array([0.,1e-9,1e-7,1e-4]);tau0=1e-9;field=2e8;activation=1e9
    expected=-np.expm1(-t/(tau0*np.exp(activation/field)))
    np.testing.assert_allclose(switching_fraction(t,field,tau0_s=tau0,activation_field_V_m=activation),expected,rtol=1e-14,atol=1e-16)
    for bad in ([-1.], [np.nan], [1j]):
        with pytest.raises(ValueError):switching_fraction(bad,field,tau0_s=tau0,activation_field_V_m=activation)


@pytest.mark.parametrize('specimen',['LT:HfO2','La:HfO2'])
def test_experiment_fitted_single_time_parameters_execute_in_native_kinetics(specimen):
    from test_physical_step_commit import native,N,PS
    curves=load_published_hafnia_curves(RAW,specimen=specimen)
    fit=fit_switching_kinetics(curves[::2],curves[1::2],rmse_budget=.1,max_error_budget=.2)
    for c in curves[1::2]:
        duration=c.times_s[len(c.times_s)//2]
        sim=native();voltage=c.nominal_field_V_m*40e-9
        sim.set_dirichlet_potential({0:0.,N-1:voltage})
        sim.set_initial_guess(np.linspace(0,voltage,N),np.zeros(N),np.zeros(N))
        sim.set_ferroelectric_nls(fit['tau0_s'],fit['activation_field_V_m'],duration)
        result=sim.solve();assert result['converged']
        predicted=switching_fraction([duration],c.nominal_field_V_m,
            tau0_s=fit['tau0_s'],activation_field_V_m=fit['activation_field_V_m'])[0]
        # This verifies normalized single-ensemble kinetics only; the native
        # 40nm fixture is not the experimental 6nm film's electrical calibration.
        np.testing.assert_allclose(-result['P'][:,0]/PS,predicted,rtol=2e-10,atol=1e-12)
