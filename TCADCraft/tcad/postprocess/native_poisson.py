"""Independent Python HMM reconstruction for the native electrostatic solve."""
import numpy as np
from tcad.solver.cut_cell_poisson import solve_cut_cell_poisson
from tcad.solver.cut_cell_transport import _array


def audit_native_cut_cell_poisson(result,mesh,permittivity_F_m,charge_density_C_m3,*,
        dirichlet_V,charge_atol_C,energy_atol_J,potential_atol_V=1e-10,electric_field_atol_V_m=1e-4):
    """Reassemble and solve in Python; never call native or supplied results."""
    for value in (charge_atol_C,energy_atol_J,potential_atol_V,electric_field_atol_V_m):
        _array(value,1,'independent native Poisson budget',positive=True)
    expected=solve_cut_cell_poisson(mesh,permittivity_F_m,charge_density_C_m3,
        dirichlet_V=dirichlet_V,charge_atol_C=charge_atol_C)
    nc=len(mesh.volumes_m3);nf=len(mesh.faces)
    ni=sum(f.neighbor>=0 for f in mesh.faces);nfree=nc+nf-len(dirichlet_V)
    errors={}
    for key,size in (('cell_potential_V',nc),('face_potential_V',nf),
            ('integrated_D_flux_C',nf),('shared_flux_mismatch_C',ni),('algebraic_residual_C',nfree)):
        actual=_array(result[key],size,key)
        errors[key]=float(np.max(abs(actual-expected[key]),initial=0.))
    electric=np.asarray(result['electric_field_V_m'])
    if electric.shape!=(nc,3) or electric.dtype.kind not in 'fiu' or not np.all(np.isfinite(electric)):
        raise ValueError('finite native electric field required')
    errors['electric_field_V_m']=float(np.max(abs(electric-expected['electric_field_V_m']),initial=0.))
    energy=float(_array(result['electrostatic_energy_J'],1,'native field energy')[0])
    errors['electrostatic_energy_J']=abs(energy-expected['electrostatic_energy_J'])
    gauss=mesh.audit_gauss(result['integrated_D_flux_C'],np.broadcast_to(charge_density_C_m3,(nc,)),
        charge_atol_C=charge_atol_C)
    claimed=result['gauss_audit']
    errors['gauss_cell_C']=float(np.max(abs(_array(claimed['cell_residual_C'],nc,'Gauss cell residual')-
        gauss['cell_residual_C']),initial=0.))
    for key in ('global_residual_C','boundary_flux_C','total_charge_C'):
        errors['gauss_'+key]=abs(float(_array(claimed[key],1,'Gauss scalar')[0])-gauss[key])
    charge_errors=[value for key,value in errors.items() if key not in (
        'cell_potential_V','face_potential_V','electric_field_V_m','electrostatic_energy_J')]
    contract=(result.get('valid') is True and result.get('execution_backend')=='native' and
        result.get('scope')=='native_scalar_epsilon_zero_polarization_hybrid_mimetic_Poisson' and
        result.get('physical_validated') is False and result.get('transport_coupled') is False and
        claimed.get('valid') is gauss['valid'])
    valid=bool(contract and expected['valid'] and gauss['valid'] and max(charge_errors,default=0.)<=charge_atol_C and
        max(errors['cell_potential_V'],errors['face_potential_V'])<=potential_atol_V and
        errors['electric_field_V_m']<=electric_field_atol_V_m and errors['electrostatic_energy_J']<=energy_atol_J)
    return dict(valid=valid,scope='independent_Python_HMM_native_Poisson_audit',errors=errors,
        max_potential_error_V=max(errors['cell_potential_V'],errors['face_potential_V']),
        max_flux_error_C=errors['integrated_D_flux_C'],gauss_audit=gauss,
        complete_device_energy=False,physical_validated=False)
