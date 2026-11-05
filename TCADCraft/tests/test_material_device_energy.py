"""Public material energy audit on native mixed-material vector states."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.postprocess.material_energy import audit_material_device_energy


@pytest.mark.parametrize('shape',[(4,3,1),(4,1,3),(1,4,3),(3,3,3)])
@pytest.mark.parametrize('partial',[False,True])
def test_public_ledger_closes_and_rejects_corrupt_source_work(shape,partial):
    from test_lk_material_multidimensional import device
    from test_lk_natural_boundary_energy import quadrature
    drive=next(a for a,n in enumerate(shape) if n>1)
    faces=''.join('xXyYzZ'[2*a:2*a+2] for a,n in enumerate(shape) if n>1 and a!=drive)
    sim,_=device(shape,partial,0,natural_faces=faces)
    sim.set_ferroelectric_builtin_field(0.);sim.set_ferroelectric_depol(0.)
    history=sim.solve_transient()
    xyz=np.array([(i,j,k) for k in range(shape[2]) for j in range(shape[1]) for i in range(shape[0])])
    spacing=[1e-8,1.3e-8,1.7e-8];axes=[np.arange(n,dtype=float)**1.3*h for n,h in zip(shape,spacing)]
    eps=8.854187817e-12*(10+.4*xyz.sum(axis=1))
    kwargs=dict(zero_d_faces=faces,space_charge_free=True,boundary_coverage_complete=True,
        energy_scale_J=1e-20,lk_field_scale_V_m=1e7,charge_scale_C=1e-17,
        energy_rtol=1e-8,lk_rtol=1e-8,charge_rtol=1e-8)
    report=audit_material_device_energy(history,axes,spacing,eps,**kwargs)
    assert report['valid'] and not report['complete_device_energy'] and not report['physical_validated']
    assert np.max(abs(report['energy_balance_residual_J']))<1e-28
    bad=deepcopy(history);bad[-1]['electrode_charges_C'][0]+=1e-16
    bad[-1]['electrode_charge_increments_C'][0]+=1e-16
    assert not audit_material_device_energy(bad,axes,spacing,eps,**kwargs)['valid']
    bad=deepcopy(history);bad[-1]['electrode_charge_increments_C'][0]+=1e-16
    with pytest.raises(ValueError,match='increments disagree'):audit_material_device_energy(bad,axes,spacing,eps,**kwargs)
    with pytest.raises(ValueError,match='space_charge'):audit_material_device_energy(history,axes,spacing,eps,**dict(kwargs,space_charge_free=False))
    with pytest.raises(ValueError,match='geometry'):audit_material_device_energy(history,axes,[v*2 for v in spacing],eps,**kwargs) if 1 in shape else audit_material_device_energy(history,[a*2 for a in axes],spacing,eps,**kwargs)


def test_stable_charge_increments_preserve_work_below_snapshot_resolution():
    from test_ferroelectric_device_energy import series
    from tcad.validation.ferroelectric_energy import audit_ferroelectric_device_energy
    args=series();q=args['electrode_charges_C'];stable=np.diff(q,axis=0).copy()
    # A constant balanced offset exercises exported Q resolution only; it does
    # not establish independent field/contact-charge reconstruction.
    args['electrode_charges_C']=q+np.array([.1,-.1])
    assert not np.any(np.diff(args['electrode_charges_C'],axis=0))
    lost=audit_ferroelectric_device_energy(**args)
    assert not lost['valid']
    restored=audit_ferroelectric_device_energy(**args,electrode_charge_increments_C=stable)
    assert restored['valid'] and restored['stable_charge_increments_used']
    np.testing.assert_allclose(restored['source_work_J'],
        np.sum(args['electrode_voltages_V'][1:]*stable,axis=1),rtol=2e-15)
