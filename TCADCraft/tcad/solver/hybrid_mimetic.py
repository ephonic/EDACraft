"""Scalar hybrid mimetic diffusion on shared polyhedra.

Linear reconstruction plus positive face stabilization, as in the HMM/SUSHI
family (Eymard et al., arXiv:0801.1430). Scalar coefficients are cellwise.
Positive definiteness does not imply a discrete maximum principle.
"""
import numpy as np
from scipy.sparse import coo_matrix,diags
from scipy.sparse.linalg import spsolve
from .cut_cell_transport import _array


class HybridMimeticOperator:
    def __init__(self,mesh):
        from tcad.mesh.polyhedral_cut_cell import CutCellMesh
        if not isinstance(mesh,CutCellMesh) or not len(mesh.volumes_m3):
            raise ValueError('nonempty shared cut-cell mesh required')
        self.mesh=mesh;self.nc=len(mesh.volumes_m3);self.nf=len(mesh.faces);self.size=self.nc+self.nf
        incident=[[] for _ in range(self.nc)]
        for f,face in enumerate(mesh.faces):
            incident[face.owner].append((f,1.))
            if face.neighbor>=0:incident[face.neighbor].append((f,-1.))
        self.local=[];rows=[];cols=[];values=[];cells=[]
        for c,neighbors in enumerate(incident):
            faces=np.array([f for f,_ in neighbors]);signs=np.array([s for _,s in neighbors])
            ids=np.r_[c,self.nc+faces]
            av=np.array([mesh.faces[f].area_vector_m2*s for f,s in neighbors])
            dx=np.array([mesh.faces[f].centroid_m-mesh.centroids_m[c] for f,_ in neighbors])
            area=np.linalg.norm(av,axis=1);distance=np.sum(av*dx,axis=1)/area
            if np.any(distance<=0):raise ValueError('cell centroid must be strictly inside faces')
            gradient=np.column_stack((-av.sum(axis=0),av.T))/mesh.volumes_m3[c]
            difference=np.column_stack((-np.ones(len(neighbors)),np.eye(len(neighbors))))
            residual=difference-dx@gradient
            matrix=mesh.volumes_m3[c]*(gradient.T@gradient)+residual.T@((area/distance)[:,None]*residual)
            self.local.append((ids,matrix,gradient,faces,signs))
            rows.extend(np.repeat(ids,len(ids)));cols.extend(np.tile(ids,len(ids)))
            values.extend(matrix.ravel());cells.extend([c]*matrix.size)
        self.rows=np.asarray(rows);self.cols=np.asarray(cols)
        self.values=np.asarray(values);self.cells=np.asarray(cells)

    def boundary(self,values):
        if not isinstance(values,dict):raise ValueError('boundary map required')
        for f,v in values.items():
            if (isinstance(f,(bool,np.bool_)) or not isinstance(f,(int,np.integer))
                    or not 0<=f<self.nf or self.mesh.faces[f].neighbor>=0
                    or isinstance(v,(bool,np.bool_)) or not np.isscalar(v)
                    or not np.isreal(v) or not np.isfinite(v)):
                raise ValueError('boundary values require finite real scalars on boundary faces')
        return {int(f):float(v) for f,v in values.items()}

    def matrix(self,coefficient):
        coefficient=_array(coefficient,self.nc,'mimetic coefficient',nonnegative=True)
        return coo_matrix((self.values*coefficient[self.cells],(self.rows,self.cols)),shape=(self.size,self.size)).tocsr()

    @staticmethod
    def _solve(matrix,rhs):
        diagonal=matrix.diagonal()
        if np.any(diagonal<=0):raise ValueError('unanchored mimetic operator')
        answer=spsolve(diags(1/diagonal)@matrix,rhs/diagonal)
        if not np.all(np.isfinite(answer)):raise ValueError('nonfinite mimetic solution')
        return answer

    def _result(self,values,coefficient,drift,drift_coefficient,dirichlet):
        flux=np.zeros(self.nf);opposite=np.zeros(self.nf);action=np.empty(self.nc)
        gradient=np.empty((self.nc,3));quadratic=np.longdouble(0)
        for c,(ids,matrix,g,faces,signs) in enumerate(self.local):
            centered=values[ids]-values[c]
            local=coefficient[c]*(matrix@centered)
            quadratic+=np.longdouble(coefficient[c])*np.sum(centered.astype(np.longdouble)*(matrix@centered))
            if drift is not None:local+=drift_coefficient[c]*(matrix@(drift[ids]-drift[c]))
            action[c]=local[0];outward=-local[1:];gradient[c]=g@centered
            owner=signs>0;flux[faces[owner]]=outward[owner];opposite[faces[~owner]]=outward[~owner]
        internal=np.array([f for f,face in enumerate(self.mesh.faces) if face.neighbor>=0],int)
        # Natural boundary flux is specified exactly. Linear-solve roundoff in
        # its local reconstruction remains visible through cell_action.
        for f,face in enumerate(self.mesh.faces):
            if face.neighbor<0 and f not in dirichlet:flux[f]=0.
        return dict(cell_values=values[:self.nc],face_values=values[self.nc:],values=values,
            flux=flux,shared_flux_mismatch=flux[internal]+opposite[internal],
            cell_action=action,gradient=gradient,quadratic=float(quadratic))

    def reconstruct(self,cell_values,coefficient,*,dirichlet=None,drift=None,drift_coefficient=None):
        """Fix cell values, solve shared face continuity, return outward flux.

        Flux represents -a grad(v) - b grad(drift). The known drift has cell
        AND face values; its stabilization is included in the constitutive law.
        Unspecified boundary faces have zero TOTAL normal flux. Zero mobility
        components carry zero flux and are excluded from the linear solve.
        """
        v=_array(cell_values,self.nc,'cell values');a=_array(coefficient,self.nc,'coefficient',nonnegative=True)
        bc=self.boundary({} if dirichlet is None else dirichlet)
        matrix=self.matrix(a);force=np.zeros(self.size);b=np.zeros(self.nc)
        if drift is not None:
            drift=_array(drift,self.size,'hybrid drift potential')
            b=_array(drift_coefficient,self.nc,'drift coefficient',nonnegative=True)
            if np.any((a==0)&(b!=0)):raise ValueError('drift requires positive diffusion')
            force=self.matrix(b)@drift
        values=np.r_[v,np.zeros(self.nf)]
        fixed=np.array([self.nc+f for f in bc],int);values[fixed]=list(bc.values())
        active=self.nc+np.flatnonzero(matrix.diagonal()[self.nc:]>0)
        free=np.setdiff1d(active,fixed)
        if len(free):
            rhs=-matrix[free,:self.nc]@v-force[free]-matrix[free][:,fixed]@values[fixed]
            values[free]=self._solve(matrix[free][:,free],rhs)
        return self._result(values,a,drift,b,bc)

    def solve(self,source_integrals,coefficient,*,dirichlet):
        """Steady -div(a grad(v)) = source, with boundary centroid values."""
        source=_array(source_integrals,self.nc,'source integrals')
        a=_array(coefficient,self.nc,'coefficient',positive=True);bc=self.boundary(dirichlet)
        if not bc:raise ValueError('Dirichlet reference required')
        matrix=self.matrix(a);values=np.zeros(self.size)
        fixed=np.array([self.nc+f for f in bc],int);values[fixed]=list(bc.values())
        free=np.setdiff1d(np.arange(self.size),fixed)
        rhs=np.r_[source,np.zeros(self.nf)]-matrix[:,fixed]@values[fixed]
        values[free]=self._solve(matrix[free][:,free],rhs[free])
        return self._result(values,a,None,np.zeros(self.nc),bc)

    def quadratic_difference(self,old,new,coefficient):
        """Factored full hybrid energy difference, including face stabilization."""
        a=_array(coefficient,self.nc,'coefficient',nonnegative=True);total=np.longdouble(0)
        for c,(ids,matrix,_,_,_) in enumerate(self.local):
            x=old['values'][ids].astype(np.longdouble)-np.longdouble(old['values'][c])
            y=new['values'][ids].astype(np.longdouble)-np.longdouble(new['values'][c])
            total+=np.longdouble(a[c])*np.sum((y-x)*(matrix.astype(np.longdouble)@(y+x)))
        return float(total)
