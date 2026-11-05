"""A held-out match cannot qualify an inconsistent calibration profile."""
from copy import deepcopy
import numpy as np
import pytest
from test_spatial_energy_transport import profile
from tcad.postprocess.spatial_energy_transport import fit_spatial_energy_flux,_design


def inconsistent(carrier='electrons',scale=1.,sign=1.,fraction=.2):
    data=[profile('train','calibration',sign),profile('weak','calibration',-sign),
          profile('unseen','holdout',-.5)]
    weak=data[1]
    for key in ('n_m3','p_m3','Fn_m2_s','Fp_m2_s','Sn_W_m2','Sp_W_m2'):
        weak[key]*=scale
    A,y=_design(weak,carrier)
    # A resolved, high-frequency discrepancy orthogonal to both fit columns.
    z=np.where(np.arange(len(y))%2,1.,-1.)
    U,_,_=np.linalg.svd(A/np.linalg.norm(A,axis=0),full_matrices=False)
    z-=U@(U.T@z);z*=fraction*np.max(abs(y))/np.max(abs(z))
    weak['Sn_W_m2' if carrier=='electrons' else 'Sp_W_m2'][2:-2]+=z
    return data


@pytest.mark.parametrize('carrier',['electrons','holes'])
@pytest.mark.parametrize('scale',[1.,1e-6])
@pytest.mark.parametrize('sign',[-1.,1.])
def test_each_calibration_profile_must_pass_its_own_error_gate(carrier,scale,sign):
    data=inconsistent(carrier,scale,sign);before=deepcopy(data)
    with pytest.raises(ValueError,match='calibration spatial energy flux exceeds relative gate'):
        fit_spatial_energy_flux(data)
    for p,old in zip(data,before):
        for key in p:np.testing.assert_equal(p[key],old[key])


@pytest.mark.parametrize('carrier',['electrons','holes'])
def test_invalid_training_rejected_before_holdout_prediction(monkeypatch,carrier):
    from tcad.postprocess import spatial_energy_transport as module
    original=module._design
    def only_training(p,carrier):
        assert p['role']=='calibration','held-out predictions must not rescue a failed training law'
        return original(p,carrier)
    monkeypatch.setattr(module,'_design',only_training)
    with pytest.raises(ValueError,match='calibration spatial energy flux exceeds relative gate'):
        module.fit_spatial_energy_flux(inconsistent(carrier))


@pytest.mark.parametrize('fraction',[.01,.029,.031,.2])
def test_prespecified_relative_gate_is_applied_without_loosening(fraction):
    data=inconsistent(fraction=fraction)
    if fraction>.03:
        with pytest.raises(ValueError,match='calibration spatial energy flux exceeds relative gate'):
            fit_spatial_energy_flux(data)
    else:
        report=fit_spatial_energy_flux(data)
        assert report['calibration_accepted'] and report['accepted']
        check=next(c for c in report['calibration_checks'] if c['case_id']=='weak' and c['carrier']=='electrons')
        assert check['maximum_peak_relative_error']==pytest.approx(fraction,rel=.04)


def test_reports_each_case_and_both_carriers_with_unchanged_inputs():
    data=[profile('train','calibration'),profile('weak','calibration',-1),profile('unseen','holdout',-.5)]
    before=deepcopy(data);report=fit_spatial_energy_flux(data)
    assert report['accepted'] and report['calibration_accepted'] and report['holdouts_accepted']
    assert len(report['calibration_checks'])==4
    for c in report['calibration_checks']:
        p=next(p for p in data if p['case_id']==c['case_id'])
        assert c['source_sha256']==p['source_sha256'] and c['role']=='calibration'
        assert c['accepted'] and c['reference_peak_W_m2']>0
        assert c['maximum_error_W_m2']<.03*c['reference_peak_W_m2']
    for p,old in zip(data,before):
        for key in p:np.testing.assert_equal(p[key],old[key])
    assert not report['physical_validated'] and not report['experimental_validated']


def test_failed_holdout_retains_training_report_and_does_not_refit():
    data=[profile('train','calibration'),profile('unseen','holdout')]
    before=fit_spatial_energy_flux(data);data[1]['Sp_W_m2']*=.5
    after=fit_spatial_energy_flux(data)
    assert after['parameters']==before['parameters']
    assert after['calibration_checks']==before['calibration_checks']
    assert after['calibration_accepted'] and not after['accepted'] and not after['holdouts_accepted']


@pytest.mark.parametrize('key',['maximum_condition','relative_gate'])
@pytest.mark.parametrize('value',[True,[.03],1j,np.inf,np.nan,0.,-1.])
def test_gates_require_positive_finite_real_scalars(key,value):
    with pytest.raises(ValueError):
        fit_spatial_energy_flux([profile('a','calibration'),profile('b','holdout')],**{key:value})


def test_positive_scalar_numpy_gates_remain_supported():
    report=fit_spatial_energy_flux([profile('a','calibration'),profile('b','holdout')],
                                 maximum_condition=np.float64(100),relative_gate=np.float64(.03))
    assert report['accepted']
