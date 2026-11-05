from dataclasses import replace,FrozenInstanceError
from copy import deepcopy
import numpy as np
import pytest
from tcad.physics.spectral_auger import SpectralAugerState,AugerEvent,spectral_auger_source,packed,FIELDS
from tcad.postprocess.spectral_auger import audit_auger_source

Q=1.602176634e-19;KB=1.380649e-23
BASE=SpectralAugerState(900,500,.8*Q,.7*Q,.6*Q,.5*Q,.067,.45)
def events(weight=1e34):
    return (AugerEvent('eeh',((1,0,0),(3,0,0),(0,0,0)),weight),
            AugerEvent('hhe',((0,1,0),(0,3,0),(0,0,0)),.3*weight))

@pytest.mark.parametrize('changes',[{},dict(temperature_n_K=1,temperature_p_K=3000),dict(temperature_n_K=3000,temperature_p_K=1),
 dict(mu_n_J=3*Q,mu_p_J=2*Q),dict(mu_n_J=-Q,mu_p_J=-Q),dict(mass_n_ratio=3,mass_p_ratio=.01),
 dict(mass_n_ratio=.01,mass_p_ratio=3),dict(Ec_J=.001*Q,Eh_J=.001*Q),
 dict(temperature_n_K=300,temperature_p_K=300,mu_n_J=.03*Q,mu_p_J=-.03*Q)])
def test_native_moments_match_independent_decimal_reference(changes):
    s=replace(BASE,**changes);r=spectral_auger_source(s,events());a=audit_auger_source(s,events(),r)
    assert a['valid'],a
    assert r['entropy_production_W_m3_K']>=0 and r['total_energy_source_W_m3']==0
    assert r['maximum_kinematic_scaled_defect']<1e-30

@pytest.mark.parametrize('channel',['eeh','hhe'])
def test_recombination_heats_third_carrier_and_impact_reverses(channel):
    ev=(AugerEvent(channel,((1,0,0),(3,0,0),(0,0,0)),1e34),)
    common=replace(BASE,temperature_n_K=1000,temperature_p_K=1000)
    a=spectral_auger_source(common,ev)
    b=spectral_auger_source(replace(common,mu_n_J=-.2*Q,mu_p_J=-.1*Q),ev)
    assert a['net_recombination_rate_m3_s']>0 and b['net_recombination_rate_m3_s']<0
    majority='electron' if channel=='eeh' else 'hole'
    assert a[majority+'_energy_source_W_m3']>0 and b[majority+'_energy_source_W_m3']<0
    assert audit_auger_source(common,ev,a)['valid']

@pytest.mark.parametrize('mu',[-.4,0,.55,1.2])
def test_common_temperature_detailed_balance(mu):
    s=replace(BASE,temperature_n_K=300,temperature_p_K=300,mu_n_J=mu*Q,mu_p_J=-mu*Q)
    r=spectral_auger_source(s,events());gross=r['auger_rate_m3_s']+r['impact_rate_m3_s']
    assert abs(r['net_recombination_rate_m3_s'])<1e-27*gross
    assert r['entropy_production_W_m3_K']<1e-50*KB*gross

def test_zero_weight_and_linear_weight():
    zero=spectral_auger_source(BASE,events(0));a=spectral_auger_source(BASE,events());b=spectral_auger_source(BASE,events(2e34))
    for k in FIELDS:
        if k=='maximum_kinematic_scaled_defect':continue
        assert zero[k]==0 and b[k]==pytest.approx(2*a[k],rel=2e-15)
    assert audit_auger_source(BASE,events(0),zero)['valid']

def test_reference_covariance():
    d=-2*Q;s=replace(BASE,Ec_J=BASE.Ec_J+d,Eh_J=BASE.Eh_J-d,mu_n_J=BASE.mu_n_J+d,mu_p_J=BASE.mu_p_J-d)
    a=spectral_auger_source(BASE,events());b=spectral_auger_source(s,events());net=a['net_recombination_rate_m3_s']
    for k in ('net_recombination_rate_m3_s','entropy_production_W_m3_K'):assert b[k]==pytest.approx(a[k],rel=2e-13)
    assert b['electron_energy_source_W_m3']==pytest.approx(a['electron_energy_source_W_m3']-d*net,rel=2e-13)
    assert b['hole_energy_source_W_m3']==pytest.approx(a['hole_energy_source_W_m3']+d*net,rel=2e-13)
    assert audit_auger_source(s,events(),b)['valid']

def test_on_shell_energy_and_momentum_geometry():
    # Noncollinear allowed geometry with both majority and minority momenta.
    ev=(AugerEvent('eeh',((1,.1,0),(3,-.1,0),(.2,0,.1)),1e34),)
    r=spectral_auger_source(BASE,ev);row=r['event_moments'][0]
    assert row['kinetic_4_J']==pytest.approx(float(BASE.Ec_J+BASE.Eh_J)+sum(row[f'kinetic_{i}_J'] for i in (1,2,3)),rel=3e-15)
    a=np.array(ev[0].momentum_shape,float);out=np.sum(a,axis=0)*row['wavevector_scale_m_inv']
    actual=(6.62607015e-34/(2*np.pi))**2*np.dot(out,out)/(2*9.1093837015e-31*float(BASE.mass_n_ratio))
    assert actual==pytest.approx(row['kinetic_4_J'],rel=3e-15)
    assert audit_auger_source(BASE,ev,r)['valid']

def test_shape_scaling_exchange_and_rotation_invariance():
    shape=np.array([[1,0,0],[3,0,0],[0,0,0]],float);a=spectral_auger_source(BASE,[AugerEvent('eeh',shape,1e34)])
    for q in (shape*7,shape[[1,0,2]],shape[:,[1,0,2]]):
        b=spectral_auger_source(BASE,[AugerEvent('eeh',q,1e34)])
        for k in FIELDS:
            if k!='maximum_kinematic_scaled_defect':assert b[k]==pytest.approx(a[k],rel=2e-14,abs=0)

def test_distinct_event_order_additivity():
    es=events();r=spectral_auger_source(BASE,es);reverse=spectral_auger_source(BASE,es[::-1])
    for k in FIELDS:assert reverse[k]==r[k]
    one=[spectral_auger_source(BASE,[e]) for e in es]
    for k in FIELDS:
        if k!='maximum_kinematic_scaled_defect':assert sum(v[k] for v in one)==pytest.approx(r[k],rel=2e-15)

def test_reference_uses_no_native_entrypoint(monkeypatch):
    es=events();r=spectral_auger_source(BASE,es)
    def fail(*a,**k):raise AssertionError('native called')
    monkeypatch.setattr('tcad.core._bindings.native_spectral_auger_raw',fail)
    assert audit_auger_source(BASE,es,r)['valid']

@pytest.mark.parametrize('field',list(FIELDS)+['coverage','event_energy','law','device_coupled','material_calibrated','continuum_kernel_integrated'])
def test_independent_audit_rejects_forgery(field):
    es=events();r=spectral_auger_source(BASE,es);bad=deepcopy(r)
    gross=r['auger_rate_m3_s']+r['impact_rate_m3_s'];energy=max(abs(r['electron_energy_source_W_m3']),gross*Q)
    if field=='coverage':bad['event_moments']=[]
    elif field=='event_energy':bad['event_moments'][0]['kinetic_4_J']+=Q
    elif field=='law':bad[field]='unknown'
    elif field in ('device_coupled','material_calibrated','continuum_kernel_integrated'):bad[field]=True
    else:
        scale=energy if field.endswith('W_m3') else (energy/300 if field.endswith('W_m3_K') else (gross*Q if field.endswith('C_m3_s') else (1 if field=='maximum_kinematic_scaled_defect' else gross)))
        bad[field]+=.01*scale
    assert not audit_auger_source(BASE,es,bad)['valid']

@pytest.mark.parametrize('value',[True,np.nan,np.inf,1j,[300.],np.array([300.]),'300'])
def test_state_rejects_non_real_scalars(value):
    with pytest.raises(ValueError):replace(BASE,temperature_n_K=value)

@pytest.mark.parametrize('change',[dict(temperature_n_K=0),dict(temperature_p_K=-1),dict(mass_n_ratio=0),dict(mass_p_ratio=-1),dict(Eh_J=-BASE.Ec_J)])
def test_state_rejects_nonphysical_parameters(change):
    with pytest.raises(ValueError):replace(BASE,**change)

@pytest.mark.parametrize('shape',[np.zeros((3,3)),np.ones((2,3)),[[1,0,0],[1,0,0],[0,0,0]],[[np.nan,0,0],[3,0,0],[0,0,0]],np.ones((3,3),complex)])
def test_reject_invalid_geometry(shape):
    with pytest.raises(ValueError):AugerEvent('eeh',shape,1e34)

@pytest.mark.parametrize('field,value',[('channel','nnn'),('weight_m3_s',-1),('weight_m3_s',True),('weight_m3_s',np.inf)])
def test_reject_invalid_event_metadata(field,value):
    with pytest.raises(ValueError):replace(events()[0],**{field:value})

def test_buffers_are_owned_and_frozen():
    shape=np.array([[1,0,0],[3,0,0],[0,0,0]],float);weight=np.array(1e34);temp=np.array(900.)
    ev=AugerEvent('eeh',shape,weight);s=replace(BASE,temperature_n_K=temp)
    before=spectral_auger_source(s,[ev]);shape[:]=0;weight[...]=0;temp[...]=1
    assert spectral_auger_source(s,[ev])==before
    with pytest.raises(FrozenInstanceError):ev.weight_m3_s=0

def test_reject_duplicate_and_empty_or_oversize_tables():
    e=events()[0]
    for table in ([],[e,e],[e]*4097):
        with pytest.raises(ValueError):spectral_auger_source(BASE,table)
    with pytest.raises(ValueError):spectral_auger_source(BASE,[e,replace(e,momentum_shape=np.array(e.momentum_shape)*2)])

@pytest.mark.parametrize('damage',['state_width','event_width','channel','weight','nan','temperature','mass','gap','forbidden','duplicate','identical'])
def test_raw_schema_rejection(damage):
    from tcad.core._bindings import native_spectral_auger_raw
    s,e=packed(BASE,[events()[0]])
    if damage=='state_width':s=s[:-1]
    elif damage=='event_width':e=e[:-1]
    elif damage=='channel':e[0]='2'
    elif damage=='weight':e[1]='-1'
    elif damage=='nan':e[2]='nan'
    elif damage=='temperature':s[0]='0'
    elif damage=='mass':s[6]='0'
    elif damage=='gap':s[4]='-1'
    elif damage=='duplicate':e=e+e
    elif damage=='identical':e[2:5]=e[5:8]
    else:e[5]='-1'
    with pytest.raises((ValueError,RuntimeError)):native_spectral_auger_raw(s,e)

@pytest.mark.parametrize('tolerance',[True,-1,0,1e-3,np.nan,[1e-10]])
def test_invalid_audit_tolerance(tolerance):
    with pytest.raises(ValueError):audit_auger_source(BASE,events(),{},rtol=tolerance)

@pytest.mark.parametrize('kind',['reference','audit'])
def test_empty_table_is_explicitly_rejected_by_reference_and_auditor(kind):
    from tcad.postprocess.spectral_auger import reference_auger_source
    with pytest.raises(ValueError):
        if kind=='reference':reference_auger_source(BASE,[])
        else:audit_auger_source(BASE,[],{})

@pytest.mark.parametrize('field',['auger_rate_m3_s','impact_rate_m3_s','entropy_production_W_m3_K'])
def test_zero_weight_event_cannot_hide_negative_quantity_under_global_budget(field):
    es=(replace(events()[0],weight_m3_s=0),events()[1]);r=spectral_auger_source(BASE,es)
    assert audit_auger_source(BASE,es,r)['valid'];bad=deepcopy(r)
    gross=r['auger_rate_m3_s']+r['impact_rate_m3_s']
    bad['event_moments'][0][field]=-1e-15*gross*(KB if field.endswith('W_m3_K') else 1)
    a=audit_auger_source(BASE,es,bad)
    assert not a['valid'] and any('event0_' in k and 'negative' in k for k in a['failures'])
