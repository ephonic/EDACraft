"""Shared-face Cartesian cut cells clipped by arbitrary convex halfspaces.

Geometry and conservative integrated fluxes; not a drift-diffusion stencil.
Planes are (nx,ny,nz,b), retaining n.dot(x)<=b in SI coordinates. Curved
surfaces need an explicit polyhedral approximation and geometry refinement.
"""
from dataclasses import dataclass
from itertools import product
import numpy as np


@dataclass(frozen=True)
class CutFace:
    vertices_m: np.ndarray
    area_vector_m2: np.ndarray  # outward from owner
    centroid_m: np.ndarray
    owner: int
    neighbor: int             # -1 means boundary
    boundary: tuple

    def __post_init__(self):
        for name in ('vertices_m','area_vector_m2','centroid_m'):
            a=np.array(getattr(self,name),dtype=float,copy=True);a.setflags(write=False)
            object.__setattr__(self,name,a)


@dataclass(frozen=True)
class CutCellMesh:
    volumes_m3: np.ndarray
    centroids_m: np.ndarray
    background_indices: np.ndarray
    faces: tuple
    region_ids: np.ndarray = None

    def __post_init__(self):
        for name in ('volumes_m3','centroids_m','background_indices'):
            a=np.array(getattr(self,name),copy=True);a.setflags(write=False)
            object.__setattr__(self,name,a)
        if self.region_ids is not None:
            a=np.array(self.region_ids,copy=True);a.setflags(write=False)
            object.__setattr__(self,'region_ids',a)

    def divergence_integrals(self, integrated_face_flux):
        """One flux per shared face, positive outward from its owner."""
        raw = np.asarray(integrated_face_flux)
        if raw.dtype.kind not in 'fiu' or raw.shape != (len(self.faces),) or not np.all(np.isfinite(raw)):
            raise ValueError('finite real integrated flux required for every shared face')
        out = np.zeros(len(self.volumes_m3),dtype=np.longdouble)
        for flux,face in zip(raw,self.faces):
            out[face.owner] += flux
            if face.neighbor >= 0: out[face.neighbor] -= flux
        return out

    def audit_gauss(self, integrated_D_flux_C, charge_density_C_m3, *, charge_atol_C):
        rho = np.asarray(charge_density_C_m3)
        if (rho.dtype.kind not in 'fiu' or rho.shape != self.volumes_m3.shape or not np.all(np.isfinite(rho))
                or isinstance(charge_atol_C,(bool,np.bool_)) or not np.isscalar(charge_atol_C)
                or not np.isfinite(charge_atol_C) or charge_atol_C < 0):
            raise ValueError('finite cell charge density and nonnegative absolute budget required')
        divergence = self.divergence_integrals(integrated_D_flux_C)
        charge = self.volumes_m3.astype(np.longdouble)*rho
        residual = divergence-charge
        boundary = sum((np.longdouble(f) for f,face in zip(integrated_D_flux_C,self.faces)
                        if face.neighbor < 0),np.longdouble(0))
        global_residual = boundary-charge.sum()
        return dict(valid=bool(np.all(abs(residual)<=charge_atol_C) and abs(global_residual)<=charge_atol_C),
            cell_residual_C=np.asarray(residual,dtype=float),global_residual_C=float(global_residual),
            boundary_flux_C=float(boundary),total_charge_C=float(charge.sum()),
            physical_validated=False,scope='shared_polyhedral_geometry_integrated_Gauss')


def _unique(points, tol=1e-13):
    result=[]
    for p in points:
        if not any(np.max(abs(p-q))<=tol for q in result): result.append(p)
    return np.asarray(result)


def _clip(faces, normal, offset, label):
    result=[]; cut=[]
    for polygon,key in faces:
        vertices=[]
        for u,v in zip(polygon,np.roll(polygon,-1,axis=0)):
            du,dv=np.dot(normal,u)-offset,np.dot(normal,v)-offset
            if du<=0: vertices.append(u)
            if (du<0 and dv>0) or (du>0 and dv<0):
                point=u+(v-u)*(du/(du-dv)); vertices.append(point); cut.append(point)
            elif du==0: cut.append(u)
        if len(vertices)>=3:
            vertices=_unique(vertices)
            if len(vertices)>=3: result.append((vertices,key))
    if cut:
        polygon=_unique(cut)
        # A coplanar existing face must not be duplicated as a clipping cap.
        if len(polygon)>=3 and not any(np.all(abs(p@normal-offset)<1e-13) for p,_ in result):
            center=polygon.mean(axis=0);n=normal/np.linalg.norm(normal)
            u=np.cross(n,np.eye(3)[np.argmin(abs(n))]);u/=np.linalg.norm(u);v=np.cross(n,u)
            angles=np.arctan2((polygon-center)@v,(polygon-center)@u)
            result.append((polygon[np.argsort(angles)],label))
    return result


def _face_geometry(polygon):
    p=polygon.astype(np.longdouble);origin=p[0]
    cross=np.cross(p[1:-1]-origin,p[2:]-origin)/2
    area=np.sqrt(np.sum(cross*cross,axis=1))
    if not np.all(np.isfinite(area)) or area.sum()<=0:
        raise ValueError('degenerate or unrepresentable cut face')
    centroid=np.sum(area[:,None]*(origin+p[1:-1]+p[2:])/3,axis=0)/area.sum()
    return np.sum(cross,axis=0),centroid


def convex_cut_cells(axis_faces_m, halfspaces):
    """Clip a 3-D background grid; keep one shared face per adjacent cell pair.

    Reject unresolved slivers rather than silently discarding charge volume.
    Coordinates are normalized before clipping, preserving SI geometry output.
    """
    if len(axis_faces_m)!=3: raise ValueError('three background face axes required')
    axes=[]
    for values in axis_faces_m:
        raw=np.asarray(values)
        if raw.dtype.kind not in 'fiu': raise ValueError('real background axes required')
        x=np.asarray(raw,dtype=float)
        if x.ndim!=1 or x.size<2 or not np.all(np.isfinite(x)) or np.any(np.diff(x)<=0):
            raise ValueError('finite increasing background face axes required')
        axes.append(x)
    origin=np.array([x[0] for x in axes]);scale=np.array([x[-1]-x[0] for x in axes])
    raw=np.asarray(halfspaces)
    if raw.size==0: raw=np.empty((0,4))
    if raw.dtype.kind not in 'fiu' or raw.ndim!=2 or raw.shape[1]!=4 or not np.all(np.isfinite(raw)):
        raise ValueError('halfspaces require finite real (M,4) array')
    planes=[]
    for row in raw:
        n=row[:3]*scale;b=row[3]-row[:3]@origin;norm=np.linalg.norm(n)
        if not np.isfinite(norm) or norm<=0: raise ValueError('nonzero representable plane normal required')
        planes.append((n/norm,b/norm))
    unit=[(x-o)/s for x,o,s in zip(axes,origin,scale)]
    all_faces=[];shared={};volumes=[];centers=[];indices=[]
    for index in product(*(range(len(x)-1) for x in axes)):
        lower=np.array([x[i] for x,i in zip(unit,index)]);upper=np.array([x[i+1] for x,i in zip(unit,index)])
        faces=[]
        for a,side in product(range(3),range(2)):
            other=[k for k in range(3) if k!=a]
            polygon=[]
            for u,v in ((0,0),(1,0),(1,1),(0,1)):
                p=lower.copy();p[a]=upper[a] if side else lower[a]
                p[other[0]]=upper[other[0]] if u else lower[other[0]]
                p[other[1]]=upper[other[1]] if v else lower[other[1]];polygon.append(p)
            polygon=np.array(polygon);direction=np.cross(polygon[1]-polygon[0],polygon[2]-polygon[0])[a]
            if (direction>0)!=bool(side): polygon=polygon[::-1]
            key=('grid',a,index[a]+side,*(index[k] for k in other))
            faces.append((polygon,key))
        for k,(n,b) in enumerate(planes): faces=_clip(faces,n,b,('plane',k,*index))
        if not faces: continue
        points=np.vstack([p for p,_ in faces]);reference=points.mean(axis=0)
        volume=np.longdouble(0);moment=np.zeros(3,dtype=np.longdouble)
        physical=[]
        for polygon,key in faces:
            p=(origin+polygon*scale).astype(np.longdouble)
            area,centroid=_face_geometry(p)
            r=(origin+reference*scale).astype(np.longdouble)
            for i in range(1,len(p)-1):
                dv=np.dot(p[0]-r,np.cross(p[i]-r,p[i+1]-r))/6
                volume+=dv;moment+=dv*(r+p[0]+p[i]+p[i+1])/4
            physical.append((np.asarray(p,dtype=float),np.asarray(area,dtype=float),np.asarray(centroid,dtype=float),key))
        background=np.prod((upper-lower).astype(np.longdouble)*scale)
        if volume<=0 or volume/background<1e-13:
            raise ValueError('unresolved cut-cell sliver; refine or change geometry')
        owner=len(volumes);volumes.append(float(volume));centers.append(np.asarray(moment/volume,dtype=float));indices.append(index)
        for p,area,centroid,key in physical:
            if key in shared:
                previous=shared[key];old=all_faces[previous]
                if old.neighbor>=0 or not np.allclose(old.area_vector_m2,-area,rtol=1e-10,atol=0):
                    raise ValueError('shared cut face is inconsistent')
                if np.max(abs((centroid-old.centroid_m)/scale))>1e-12:
                    raise ValueError('shared cut-face centroid mismatch')
                all_faces[previous]=CutFace(old.vertices_m,old.area_vector_m2,old.centroid_m,old.owner,owner,key)
            else:
                shared[key]=len(all_faces);all_faces.append(CutFace(p,area,centroid,owner,-1,key))
    return CutCellMesh(np.asarray(volumes),np.asarray(centers).reshape(-1,3),
                       np.asarray(indices,dtype=int).reshape(-1,3),tuple(all_faces))
