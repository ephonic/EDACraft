"""Independent local-row reference, decimal density and actual native dispatch."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.core._bindings import native_three_temperature_local_raw
from tcad.physics.native_fermi_local import _decimal
from test_three_temperature import case,BUDGET


def inputs():
    # Two asymmetric cells and three oriented faces: internal, left, right.
    c=np.array([[1e25,2e25,300,1.001e25,1.998e25,302,1e8,1e8+3,1e8-2,
                 2e8,2e8-4,2e8+1,2e-21,10,.01,.02,.001,2e-13,5e-13],
                [1e25,2e25,310,1.002e25,1.999e25,308,1e8,1e8+1,1e8-1,
                 2e8,2e8+2,2e8+3,3e-21,20,.03,.04,.004,3e-13,7e-13]],dtype=np.longdouble)
    f=np.array([[0,1,2e10,-3e10,1e-9,-2e-9,.02,.03,1e-14,1e-8,3e-8,0,0],
                [0,-1,-1e10,2e10,-2e-9,1e-9,0,0,1e-14,1e-8,0,295,1],
                [1,-1,3e10,-1e10,3e-9,-4e-9,.05,.05,1e-14,2e-8,0,315,1]],dtype=np.longdouble)
    return c,f,2e-13


def run(c,f,dt):
    return np.array(native_three_temperature_local_raw(
        [_decimal(v) for v in c.ravel()],[_decimal(v) for v in f.ravel()],dt))


def reference(c,f,dt):
    count=len(c);r=np.zeros((12,count),dtype=np.longdouble);heat=[]
    dt=np.longdouble(dt);q=np.longdouble('1.602176634e-19')
    for i,a in enumerate(c):
        r[:7,i]=[a[12]*(a[3]-a[0]),a[12]*(a[4]-a[1]),a[12]*(a[7]-a[6]),
            a[12]*(a[10]-a[9]),a[12]*a[13]*(a[5]-a[2]),
            dt*a[12]*(a[7]-a[8])/a[17],dt*a[12]*(a[10]-a[11])/a[18]]
        r[9,i]=r[2,i]+r[5,i];r[10,i]=r[3,i]+r[6,i];r[11,i]=r[4,i]-r[5,i]-r[6,i]
    for a in f:
        i,j=map(int,a[:2]);h=0
        if j>=0:h=a[8]/(a[9]/c[i,16]+a[10]/c[j,16])*(c[i,5]-c[j,5])
        elif a[12]:h=a[8]*c[i,16]/a[9]*(c[i,5]-a[11])
        heat.append(h)
        for cell,orientation in [(i,1)]+([(j,-1)] if j>=0 else []):
            voltage=(c[cell,14]+c[cell,15]-a[6]-a[7])/2
            wn=-dt*q*orientation*a[2]*voltage;wp=dt*q*orientation*a[3]*voltage
            r[0,cell]+=dt*orientation*a[2];r[1,cell]+=dt*orientation*a[3]
            r[7,cell]+=wn;r[8,cell]+=wp
            r[9,cell]+=dt*orientation*a[4]-wn;r[10,cell]+=dt*orientation*a[5]-wp
            r[11,cell]+=dt*orientation*h
    return np.r_[r.ravel(),heat].astype(float)


def test_all_local_components_match_independent_reference():
    c,f,dt=inputs();actual=run(c,f,dt);expected=reference(c,f,dt)
    np.testing.assert_allclose(actual,expected,rtol=2e-12,atol=1e-32)
    # A single electrical-work sum must not erase the separate carrier rows.
    assert not np.array_equal(actual[7*2:8*2],actual[8*2:9*2])


def test_density_delta_below_float64_spacing_survives_decimal_boundary():
    c,f,dt=inputs();f[:,2:6]=0
    c[:,3]=c[:,0]+np.longdouble(5e8);c[:,4]=c[:,1]
    assert float(c[0,3])==float(c[0,0])
    actual=run(c,f,dt)
    np.testing.assert_allclose(actual[:2],np.array(c[:,12]*(c[:,3]-c[:,0]),float),rtol=2e-12,atol=0)
    assert np.all(actual[:2]>0)


def test_reversing_internal_face_preserves_cell_rows():
    c,f,dt=inputs();before=run(c,f,dt)
    f[0,[0,1]]=f[0,[1,0]];f[0,2:6]*=-1;f[0,[9,10]]=f[0,[10,9]]
    after=run(c,f,dt)
    np.testing.assert_allclose(after[:24],before[:24],rtol=2e-12,atol=1e-32)
    assert after[24]==pytest.approx(-before[24],rel=2e-12)


def test_graded_thermal_resistance_uses_each_half_distance():
    c,f,dt=inputs();actual=run(c,f,dt)
    expected=f[0,8]/(f[0,9]/c[0,16]+f[0,10]/c[1,16])*(c[0,5]-c[1,5])
    assert actual[24]==pytest.approx(float(expected),rel=2e-12)
    wrong=2*c[0,16]*c[1,16]/(c[0,16]+c[1,16])*f[0,8]/sum(f[0,9:11])*(c[0,5]-c[1,5])
    assert abs(actual[24]/wrong-1)>.1


def test_closed_relaxation_cancels_in_total_energy_without_repair():
    c,f,dt=inputs();f[:,2:6]=0;f=f[:1]
    actual=run(c,f,dt);rows=actual[:24].reshape(12,2)
    np.testing.assert_allclose(np.sum(rows[9:12],axis=0),np.sum(rows[2:5],axis=0)+
        dt*np.array([actual[24],-actual[24]]),rtol=2e-12,atol=1e-32)


@pytest.mark.parametrize('damage',['empty','cell_width','face_width','nan','infinity','trailing',
    'bad_owner','fractional_owner','same_owner','bad_neighbor','negative_distance','boundary_distance',
    'bath_on_internal','bath_flag','unflagged_bath','negative_capacity','negative_tau','negative_density'])
def test_raw_invalid_state_geometry_and_parameters_rejected(damage):
    c,f,dt=inputs();c=c.copy();f=f.copy()
    cp=[_decimal(v) for v in c.ravel()];fp=[_decimal(v) for v in f.ravel()]
    if damage=='empty':cp=[]
    if damage=='cell_width':cp.pop()
    if damage=='face_width':fp.pop()
    if damage=='nan':cp[0]='nan'
    if damage=='infinity':fp[2]='inf'
    if damage=='trailing':cp[0]='1x'
    for key,index,value in [('bad_owner',0,3),('fractional_owner',0,.5),('same_owner',1,0),
        ('bad_neighbor',1,-2),('negative_distance',9,-1),('boundary_distance',13+10,1),
        ('bath_on_internal',12,1),('bath_flag',12,2),('unflagged_bath',11,300)]:
        if damage==key:fp[index]=str(value)
    for key,index in [('negative_capacity',13),('negative_tau',17),('negative_density',3)]:
        if damage==key:cp[index]='-1'
    with pytest.raises(ValueError):native_three_temperature_local_raw(cp,fp,dt)


@pytest.mark.parametrize('dt',[0.,-1.,float('nan'),float('inf')])
def test_raw_invalid_time_rejected(dt):
    c,f,_=inputs()
    with pytest.raises(ValueError):run(c,f,dt)


def test_actual_step_calls_native_rows_and_no_python_conduction(monkeypatch):
    import tcad.core._bindings as bindings
    original=bindings.native_three_temperature_local_raw;calls=[]
    def observed(*a):calls.append(1);return original(*a)
    monkeypatch.setattr(bindings,'native_three_temperature_local_raw',observed)
    model,old=case(count=1,uniform=True)
    model.residual_orchestration='python'  # Explicit local-row reference mode.
    def forbidden(*a):raise AssertionError('Python production conduction called')
    monkeypatch.setattr(model,'conduction',forbidden)
    new,report=model.step(old,2e-13,**BUDGET)
    assert calls and new.time_s>0 and report['independent_audit']['valid']
    assert report['residual_backend']==report['local_conservation_backend']=='native'
    assert report['residual_orchestration']=='python'


def test_native_error_propagates_without_python_fallback(monkeypatch):
    import tcad.core._bindings as bindings
    model,old=case(count=1,uniform=True);saved=old.n_m3.tobytes()
    model.residual_orchestration='python'  # Failure propagation of the local-row entry.
    def fail(*args):raise ValueError('forced native local failure')
    monkeypatch.setattr(bindings,'native_three_temperature_local_raw',fail)
    with pytest.raises(ValueError,match='forced native'):model.step(old,2e-13,**BUDGET)
    assert old.time_s==0 and old.n_m3.tobytes()==saved


@pytest.mark.parametrize('field',['residual_backend','local_conservation_backend','residual_orchestration'])
def test_audit_rejects_forged_backend_metadata(field):
    from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy
    model,old=case(count=1,uniform=True);new,report=model.step(old,2e-13,**BUDGET)
    bad=deepcopy(report);bad[field]='unknown'
    assert not audit_three_temperature_energy(model,old,new,bad,**BUDGET)['valid']
