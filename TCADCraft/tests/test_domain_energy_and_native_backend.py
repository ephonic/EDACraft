import numpy as np
import pytest

from tcad.physics.native_backend import configure_native_multivalley
from tcad.validation.ferroelectric_domain_energy import audit_domain_energy


class DummyNative:
    def __init__(self): self.calls=[]
    def set_statistics_type(self, value): self.calls.append(('statistics', value))
    def set_density_gradient_silicon_multivalley(self, *args): self.calls.append(('multivalley', args))


def _history():
    t=np.array([0.,1e-9,2e-9]); p=np.zeros((3,2,3)); p[1,:,0]=.02; p[2,:,0]=.04
    grad=np.zeros((3,2,3,3)); grad[:,0,0,0]=[0.,1e6,2e6]; grad[:,1,0,0]=[0.,-1e6,-2e6]
    vol=np.array([1e-21,1e-21]); a=np.array([-1e8,-1.2e8]); b=np.array([2e10,2.2e10]); gamma=np.array([1e-7,1.1e-7])
    # Select endpoint field so work exactly balances storage + LK loss.
    provisional=np.zeros_like(p)
    for k in (1,2):
        provisional[k,:,0]=1e8
    return t,p,grad,vol,a,b,gamma,provisional


def test_native_configuration_bridge_forwards_fd_and_valleys():
    native=DummyNative(); report=configure_native_multivalley(native)
    assert report['native_backend_configured'] and report['statistics']=='fermi_dirac'
    assert native.calls[0]==('statistics',1) and native.calls[1][0]=='multivalley'


def test_domain_gradient_energy_is_included_and_restricted():
    t,p,grad,vol,a,b,gamma,e=_history()
    # Choose work from the exact audited storage and loss terms.
    kap=np.diag([1e-12,1e-12,1e-12])
    landau=lambda x: np.sum(.5*a[None,:,None]*x*x,axis=2)+.25*b[None,:]*(np.sum(x*x,axis=2)**2)
    landau_e=np.sum(landau(p),axis=1)*vol[0]
    grad_e=.5*np.einsum('tcij,ij,tcij,c->t',grad,kap,grad,vol)
    loss=np.sum(gamma[None,:,None]*np.diff(p,axis=0)**2/np.diff(t)[:,None,None],axis=(1,2))*vol[0]
    desired=np.diff(landau_e+grad_e)+loss
    e[1:,0,0]=desired/(np.sum(np.diff(p,axis=0)[:, :, 0],axis=1)*vol[0])
    e[1:,1,0]=e[1:,0,0]
    report=audit_domain_energy(t,p,grad,vol,kap,a,b,gamma,e,converged=True,energy_scale_J=1e-12,energy_rtol=1e-8)
    assert report['valid'] and np.any(report['domain_gradient_storage_change_J']!=0)
    assert report['complete_device_energy'] is False


def test_domain_energy_rejects_unconverged_history():
    t,p,g,vol,a,b,gamma,e=_history()
    with pytest.raises(ValueError,match='converged'):
        audit_domain_energy(t,p,g,vol,1e-12,a,b,gamma,e,converged=[True,False,True],energy_scale_J=1e-12)
