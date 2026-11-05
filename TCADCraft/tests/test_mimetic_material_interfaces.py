"""Independent exact flux across an oblique scalar conductivity jump."""
import numpy as np
import pytest
from tcad.mesh.polyhedral_regions import region_cut_cells
from tcad.solver.hybrid_mimetic import HybridMimeticOperator


@pytest.mark.parametrize('contrast',[1.,10.,1000.])
def test_oblique_discontinuous_conductivity_preserves_exact_normal_flux(contrast):
    L=1e-7;normal=np.array([1.,.37,0.]);offset=.53*L
    mesh=region_cut_cells([np.linspace(0,L,4),np.linspace(0,L,4),np.array([0.,L])],
        {'left':[[[*normal,offset]]],'right':[[[*(-normal),-offset]]]})
    operator=HybridMimeticOperator(mesh)
    signed=mesh.centroids_m@normal-offset
    kappa=np.where(signed<=0,1.,contrast)
    def value(x):
        s=x@normal-offset
        return 300.+1e8*s/(1. if s<=0 else contrast)
    bc={f:value(face.centroid_m) for f,face in enumerate(mesh.faces) if face.neighbor<0}
    result=operator.solve(np.zeros(operator.nc),kappa,dirichlet=bc)
    expected=np.array([-1e8*normal@face.area_vector_m2 for face in mesh.faces])
    np.testing.assert_allclose(result['cell_values'],[value(x) for x in mesh.centroids_m],atol=2e-10)
    np.testing.assert_allclose(result['flux'],expected,rtol=2e-9,atol=2e-13)
    assert max(abs(result['shared_flux_mismatch']))<2e-13
