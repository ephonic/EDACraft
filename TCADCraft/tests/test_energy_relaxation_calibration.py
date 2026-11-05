"""Independent coefficient recovery, identifiability, holdouts and native use."""
from dataclasses import replace,FrozenInstanceError
from copy import deepcopy
import hashlib,json,itertools
import numpy as np
import pytest
from tcad.material.energy_relaxation_calibration import (
    RelaxationExchangeCondition as Condition,calibrate_energy_relaxation_power_law as fit,
    fitted_relaxation_configuration as configuration,load_relaxation_exchange_condition as load)
from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw as Law

TRUTH={'electrons':(1e-13,.6,1.2,-.25),'holes':(4e-13,-.4,.8,.15)}


def observations():
    result=[]
    for carrier,(tau0,a,b,c) in TRUTH.items():
        for i,(n,Tl) in enumerate(itertools.product((8e24,1.2e25),(280.,340.))):
            # Four whole conditions, each containing independent hot/cold states.
            Tc=np.array([260.,300.,360.,400.]);N=np.full(4,n);L=np.full(4,Tl)
            tau=tau0*(L/300.)**a*(Tc/300.)**b*(N/1e25)**c
            # Positive heat capacity closure independent of the production law.
            du=(Tc-L)*N*1.5*1.380649e-23
            result.append(Condition('train-'+str(i),carrier,'calibration',N,Tc,L,
                du,du/tau,np.full(4,.01),hashlib.sha256(('training export'+str(i)).encode()).hexdigest(),
                'synthetic','test: analytic signed exchange '+str(i),'synthetic fixed-band model'))
        Tc=np.array([260.,320.,380.]);N=np.full(3,1e25);L=np.full(3,300.)
        tau=tau0*(L/300.)**a*(Tc/300.)**b*(N/1e25)**c;du=(Tc-L)*N*1.5*1.380649e-23
        result.append(Condition('hold',carrier,'holdout',N,Tc,L,du,du/tau,np.full(3,.01),
            hashlib.sha256(b'unseen export').hexdigest(),'synthetic','test: unseen condition','synthetic fixed-band model'))
    return result


def test_recover_all_eight_parameters_with_conditional_uncertainty_and_holdouts():
    result=fit(observations());assert result['fit_accepted']
    json.dumps(result,allow_nan=False)
    for carrier,truth in TRUTH.items():
        p=result['parameters'][carrier]
        actual=[p['tau0_s'],*[p['law'][k] for k in ('lattice_temperature_exponent','carrier_temperature_exponent','density_exponent')]]
        np.testing.assert_allclose(actual,truth,rtol=1e-9,atol=0)
        C=np.asarray(p['conditional_log_parameter_covariance'])
        assert np.linalg.eigvalsh(C).min()>0 and p['design_rank']==4
        assert p['training_observations']==16 and len(p['calibration_condition_ids'])==4
    assert all(h['maximum_relative_error']<1e-10 and h['accepted'] for h in result['holdouts'])
    for flag in ('provenance_authenticated','state_dependent_relaxation_calibrated','commercial_validated',
                 'experimental_validated','physical_validated','complete_device_energy'):
        assert result[flag] is False


def test_holdout_power_and_uncertainty_never_change_fit_or_covariance():
    data=observations();before=fit(data)
    data[4]=replace(data[4],power_to_lattice_W_m3=data[4].power_to_lattice_W_m3*2,
                    log_tau_standard_uncertainty=np.full(3,.02))
    after=fit(data)
    assert before['parameters']==after['parameters']
    assert not after['fit_accepted'] and not after['holdouts_accepted']
    with pytest.raises(ValueError,match='accepted'):configuration(after)


def test_training_misfit_is_reported_even_with_loose_holdout_gate():
    data=observations();power=data[0].power_to_lattice_W_m3.copy();power[0]*=1.2
    data[0]=replace(data[0],power_to_lattice_W_m3=power)
    result=fit(data,holdout_relative_gate=1.,standardized_error_gate=3.)
    assert not result['training_accepted'] and not result['fit_accepted']


def test_outside_training_envelope_is_not_certified_by_perfect_formula():
    data=observations();old=data[4];n=old.density_m3*3
    # Preserve the exact law while moving the entire unseen condition out of range.
    data[4]=replace(old,density_m3=n,power_to_lattice_W_m3=old.power_to_lattice_W_m3/3**TRUTH['electrons'][3])
    result=fit(data)
    h=result['holdouts'][0]
    assert h['maximum_relative_error']<1e-10
    assert not h['within_training_coordinate_envelope'] and not h['accepted']


def test_reference_change_reparameterizes_without_changing_effective_times():
    result=fit(observations(),reference_temperature_K=320.,reference_density_m3=1.1e25)
    assert result['fit_accepted']
    for carrier,(tau0,a,b,c) in TRUTH.items():
        p=result['parameters'][carrier]
        assert p['tau0_s']==pytest.approx(tau0*(320/300)**(a+b)*1.1**c,rel=1e-10)
        assert p['law']['reference_temperature_K']==320.
        assert p['law']['reference_density_m3']==1.1e25


def test_covariance_matches_independent_weighted_normal_matrix():
    data=observations();result=fit(data);rows=[];weights=[]
    for c in data:
        if c.carrier=='electrons' and c.role=='calibration':
            rows.extend(np.column_stack((np.ones(len(c.density_m3)),np.log(c.lattice_temperature_K/300),
                np.log(c.carrier_temperature_K/300),np.log(c.density_m3/1e25))))
            weights.extend(1/c.log_tau_standard_uncertainty**2)
    X=np.asarray(rows);expected=np.linalg.inv(X.T@(np.asarray(weights)[:,None]*X))
    np.testing.assert_allclose(result['parameters']['electrons']['conditional_log_parameter_covariance'],expected,rtol=1e-10,atol=1e-15)


def test_heteroscedastic_fit_and_predictive_uncertainty_match_independent_normal_equations():
    data=observations()
    for i,c in enumerate(data):
        if c.role=='calibration':
            sigma=np.array([.01,.02,.03,.04])
            noise=np.array([.2,-.3,.1,-.2])*sigma
            data[i]=replace(c,log_tau_standard_uncertainty=sigma,
                            power_to_lattice_W_m3=c.power_to_lattice_W_m3*np.exp(-noise))
    result=fit(data);assert result['fit_accepted']
    train=[c for c in data if c.carrier=='electrons' and c.role=='calibration']
    X=np.concatenate([np.column_stack((np.ones(4),np.log(c.lattice_temperature_K/300),
        np.log(c.carrier_temperature_K/300),np.log(c.density_m3/1e25))) for c in train])
    y=np.concatenate([np.log(abs(c.energy_difference_J_m3)/abs(c.power_to_lattice_W_m3)) for c in train])
    sigma=np.concatenate([c.log_tau_standard_uncertainty for c in train]);W=1/sigma**2
    C=np.linalg.inv(X.T@(W[:,None]*X));expected=C@X.T@(W*y)
    p=result['parameters']['electrons']
    actual=np.r_[np.log(p['tau0_s']),[p['law'][k] for k in p['log_parameter_order'][1:]]]
    np.testing.assert_allclose(actual,expected,rtol=1e-9,atol=1e-10)
    c=data[4];Z=np.column_stack((np.ones(3),np.log(c.lattice_temperature_K/300),
        np.log(c.carrier_temperature_K/300),np.log(c.density_m3/1e25)))
    predictive=np.sqrt(c.log_tau_standard_uncertainty**2+np.diag(Z@C@Z.T))
    np.testing.assert_allclose(result['holdouts'][0]['predictive_log_tau_standard_uncertainty'],predictive,rtol=1e-10)


def document():
    data=observations()
    return dict(schema='tcad.local_relaxation_exchange.v1',
        units=dict(density='m^-3',temperature='K',energy_density='J/m^3',power_density='W/m^3',log_tau_uncertainty='1'),
        condition_id='raw-training',role='calibration',source_kind='synthetic',
        source_reference='test: exact bytes',material_model=data[0].material_model,
        carriers=[{key:(getattr(c,key).tolist() if isinstance(getattr(c,key),np.ndarray) else getattr(c,key))
            for key in ('carrier','density_m3','carrier_temperature_K','lattice_temperature_K',
                        'energy_difference_J_m3','power_to_lattice_W_m3','log_tau_standard_uncertainty')}
            for c in (data[0],data[5])])


def test_exact_json_source_hash_carrier_alignment_and_no_unit_conversion(tmp_path):
    p=tmp_path/'condition.json';raw=json.dumps(document()).encode();p.write_bytes(raw)
    rows=load(p)
    assert len(rows)==2 and {c.carrier for c in rows}=={'electrons','holes'}
    assert all(c.source_sha256==hashlib.sha256(raw).hexdigest() for c in rows)
    np.testing.assert_array_equal(rows[0].density_m3,observations()[0].density_m3)


@pytest.mark.parametrize('kind',['units','schema','missing_power','forged_hash','duplicate_carrier','mixed_role','empty'])
def test_malformed_source_export_rejected(tmp_path,kind):
    d=document()
    if kind=='units':d['units']['density']='cm^-3'
    if kind=='schema':d['schema']='temperature_decay'
    if kind=='missing_power':del d['carriers'][0]['power_to_lattice_W_m3']
    if kind=='forged_hash':d['carriers'][0]['source_sha256']='a'*64
    if kind=='duplicate_carrier':d['carriers'][1]['carrier']='electrons'
    if kind=='mixed_role':d['carriers'][0]['role']='holdout'
    if kind=='empty':d['carriers']=[]
    p=tmp_path/'bad.json';p.write_text(json.dumps(d))
    with pytest.raises(ValueError):load(p)


def test_inputs_are_immutable_owned_and_fit_does_not_change_observations():
    data=observations();before=[c.power_to_lattice_W_m3.tobytes() for c in data]
    fit(data)
    assert before==[c.power_to_lattice_W_m3.tobytes() for c in data]
    with pytest.raises(ValueError):data[0].density_m3.setflags(write=True)
    with pytest.raises(FrozenInstanceError):data[0].role='holdout'
    x=np.array([1e25]);c=replace(data[0],density_m3=np.repeat(x,4));x[0]=2e25
    assert np.all(c.density_m3==1e25)


@pytest.mark.parametrize('kind',['no_holes','no_holdout','duplicate','condition_leak','source_leak',
 'material','source_kind','constant_density','collinear','ill_conditioned','bounds','exponent_bound'])
def test_leakage_rank_conditioning_and_invalid_identification_are_rejected(kind):
    data=observations();kwargs={}
    if kind=='no_holes':data=[c for c in data if c.carrier=='electrons']
    if kind=='no_holdout':data=[c for c in data if c.role=='calibration']
    if kind=='duplicate':data.append(data[0])
    if kind=='condition_leak':data[4]=replace(data[4],condition_id='train-0')
    if kind=='source_leak':data[4]=replace(data[4],source_sha256=data[0].source_sha256)
    if kind=='material':data[0]=replace(data[0],material_model='other')
    if kind=='source_kind':data[0]=replace(data[0],source_kind='measured')
    if kind=='constant_density':data=[replace(c,density_m3=np.full(len(c.density_m3),1e25)) for c in data]
    if kind in ('collinear','ill_conditioned'):
        data=[replace(c,density_m3=1e25*(c.lattice_temperature_K/300)**2*
            (1 if kind=='collinear' else np.exp(np.arange(len(c.density_m3))*1e-9))) for c in data]
    if kind=='bounds':kwargs['tau0_bounds_s']=(2e-13,3e-13)
    if kind=='exponent_bound':kwargs['exponent_bound']=.1
    with pytest.raises(ValueError):fit(data,**kwargs)


@pytest.mark.parametrize('change',[
 {'condition_id':''},{'source_sha256':'x'},{'source_reference':''},{'source_kind':'unknown'},
 {'role':'test'},{'carrier':'both'},{'material_model':''},
 {'density_m3':np.ones(4,dtype=bool)},{'density_m3':np.full(4,1e25+1j)},
 {'carrier_temperature_K':np.full(4,np.nan)},{'lattice_temperature_K':np.zeros(4)},
 {'energy_difference_J_m3':np.zeros(4)}, {'power_to_lattice_W_m3':np.zeros(4)},
 {'power_to_lattice_W_m3':np.ones(4)}, {'log_tau_standard_uncertainty':np.zeros(4)},
 {'log_tau_standard_uncertainty':np.ones(2)}, {'energy_difference_definition':'MB_temperature_slope'},
 {'power_definition':'total_device_heating'}])
def test_invalid_observations_and_misidentified_exchange_are_rejected(change):
    with pytest.raises(ValueError):replace(observations()[0],**change)


@pytest.mark.parametrize('change',[
 {'reference_temperature_K':True},{'reference_density_m3':0}, {'exponent_bound':np.nan},
 {'maximum_design_condition':1}, {'standardized_error_gate':False},
 {'holdout_relative_gate':-1}, {'tau0_bounds_s':(1e-13,1e-14)}])
def test_invalid_configuration_rejected(change):
    with pytest.raises(ValueError):fit(observations(),**change)


def test_report_cannot_gain_physical_acceptance_from_source_labels():
    for kind in ('commercial','measured'):
        result=fit([replace(c,source_kind=kind) for c in observations()])
        assert result['fit_accepted']
        assert not result['provenance_authenticated'] and not result['experimental_validated']
        assert not result['commercial_validated'] and not result['state_dependent_relaxation_calibrated']


def test_fitted_configuration_drives_native_device_and_independent_audit():
    from test_three_temperature import case,BUDGET
    from tcad.solver.device_three_temperature import DeviceThreeTemperature
    from tcad.solver.three_temperature import ThreeTemperatureElectrothermal
    cfg=configuration(fit(observations()))
    fitted,initial=case(count=1,uniform=True);truth=deepcopy(fitted)
    # Exercise the public constructor with the export rather than mutating only a tuple.
    kwargs=dict(mesh=fitted.mesh,permittivity_F_m=fitted.eps,dirichlet_V=fitted.bc,
        mobility_n_m2_Vs=fitted.mn,mobility_p_m2_Vs=fitted.mp,Ec_J=fitted.Ec,Eh_J=fitted.Eh,
        heat_capacity_J_m3_K=fitted.capacity,thermal_conductivity_W_m_K=fitted.conductivity,
        valleys_n=fitted.valleys['electrons'],valleys_p=fitted.valleys['holes'],
        thermionic_faces=fitted.thermionic_faces,particle_contacts=fitted.contacts,
        heat_bath_K=fitted.bath,terminal_groups=fitted.groups,**cfg)
    actual=DeviceThreeTemperature(ThreeTemperatureElectrothermal(**kwargs),initial)
    truth.relaxation_laws=tuple(Law(300.,1e25,*TRUTH[c][1:]) for c in ('electrons','holes'))
    expected=DeviceThreeTemperature(truth,initial)
    for _ in range(2):
        state,report=actual.advance(2e-13,**BUDGET);control,reference=expected.advance(2e-13,**BUDGET)
        assert report['independent_audit']['valid'] and reference['independent_audit']['valid']
        for field in ('electron_temperature_K','hole_temperature_K','temperature_K'):
            np.testing.assert_allclose(getattr(state,field),getattr(control,field),rtol=0,atol=1e-6)
        for carrier in ('electrons','holes'):
            np.testing.assert_allclose(report['cell_relaxation_time_s'][carrier],
                reference['cell_relaxation_time_s'][carrier],rtol=1e-10)
