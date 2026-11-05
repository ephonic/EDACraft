"""Conforming plane arrangement for nonconvex unions of material regions.

Each named region is a union of convex halfspace pieces. All region planes
split every intersected background cell before classification, so interfaces
and partial faces agree on both sides. Different material interiors may not
overlap; overlaps between pieces of the same region are counted once.
"""
from itertools import product
import numpy as np
from .polyhedral_cut_cell import CutCellMesh,CutFace,_clip,_face_geometry


def region_cut_cells(axis_faces_m, regions, *, max_fragments=100000):
    """Build owned SI geometry. ``regions`` maps string IDs to lists of (M,4) arrays."""
    if (not isinstance(regions,dict) or not regions or any(not isinstance(k,str) or not k for k in regions)
            or isinstance(max_fragments,bool) or not isinstance(max_fragments,int) or max_fragments<=0):
        raise ValueError('named regions and positive integer fragment limit required')
    if len(axis_faces_m)!=3:raise ValueError('three face axes required')
    axes=[]
    for x in axis_faces_m:
        a=np.asarray(x)
        if a.dtype.kind not in 'fiu' or a.ndim!=1 or a.size<2 or not np.all(np.isfinite(a)) or np.any(np.diff(a)<=0):
            raise ValueError('finite increasing real face axes required')
        axes.append(a.astype(float))
    origin=np.array([a[0] for a in axes]);scale=np.array([a[-1]-a[0] for a in axes])
    unit=[(a-o)/s for a,o,s in zip(axes,origin,scale)]
    planes=[];members={}
    for name,pieces in regions.items():
        if not isinstance(pieces,(list,tuple)) or not pieces:raise ValueError('nonempty convex piece lists required')
        members[name]=[]
        for piece in pieces:
            raw=np.asarray(piece)
            if raw.size==0:raw=np.empty((0,4))
            if raw.dtype.kind not in 'fiu' or raw.ndim!=2 or raw.shape[1]!=4 or not np.all(np.isfinite(raw)):
                raise ValueError('finite real (M,4) halfspaces required')
            normalized=[]
            for row in raw:
                n=row[:3]*scale;b=row[3]-row[:3]@origin;norm=np.linalg.norm(n)
                if not np.isfinite(norm) or norm<=0:raise ValueError('nonzero representable normal required')
                n=n/norm;b=b/norm;normalized.append((n,b))
                canonical=np.r_[n,b]
                if n[np.flatnonzero(abs(n)>1e-14)[0]]<0:canonical=-canonical
                close=[p for p in planes if np.max(abs(canonical-p))<1e-13]
                if close and not any(np.max(abs(canonical-p))<=8*np.finfo(float).eps*max(1.,abs(b)) for p in close):
                    raise ValueError('unresolved nearly coincident region planes')
                if not close:planes.append(canonical)
            members[name].append(normalized)
    cells=[];background=[];labels=[]
    for index in product(*(range(a.size-1) for a in unit)):
        lo=np.array([a[i] for a,i in zip(unit,index)]);hi=np.array([a[i+1] for a,i in zip(unit,index)])
        faces=[]
        for axis,side in product(range(3),range(2)):
            other=[a for a in range(3) if a!=axis];poly=[]
            for u,v in ((0,0),(1,0),(1,1),(0,1)):
                p=lo.copy();p[axis]=hi[axis] if side else lo[axis]
                p[other]=[hi[other[0]] if u else lo[other[0]],hi[other[1]] if v else lo[other[1]]];poly.append(p)
            poly=np.array(poly)
            if (np.cross(poly[1]-poly[0],poly[2]-poly[0])[axis]>0)!=bool(side):poly=poly[::-1]
            faces.append((poly,('background',axis,index[axis]+side)))
        fragments=[faces]
        for k,plane in enumerate(planes):
            split=[];n,b=plane[:3],plane[3]
            for faces in fragments:
                distances=np.vstack([p for p,_ in faces])@n-b
                if distances.min() < -1e-13 and distances.max() > 1e-13:
                    split.extend((_clip(faces,n,b,('interface_plane',k)),_clip(faces,-n,-b,('interface_plane',k))))
                else:split.append(faces)
            fragments=split
            if len(cells)+len(fragments)>max_fragments:raise ValueError('plane arrangement exceeds fragment limit')
        for faces in fragments:
            point=np.vstack([p for p,_ in faces]).mean(axis=0)
            inside=[name for name,pieces in members.items()
                if any(all(n@point<=b+1e-13 for n,b in piece) for piece in pieces)]
            if len(inside)>1:raise ValueError('different material region interiors overlap')
            if inside:cells.append(faces);background.append(index);labels.append(inside[0])
    volumes=[];centers=[];all_faces=[];shared={}
    for owner,faces in enumerate(cells):
        ref=origin+np.vstack([p for p,_ in faces]).mean(axis=0)*scale
        volume=np.longdouble(0);moment=np.zeros(3,np.longdouble)
        for polygon,label in faces:
            p=(origin+polygon*scale).astype(np.longdouble);r=ref.astype(np.longdouble)
            av,center=_face_geometry(p)
            for i in range(1,len(p)-1):
                dv=np.dot(p[0]-r,np.cross(p[i]-r,p[i+1]-r))/6
                volume+=dv;moment+=dv*(r+p[0]+p[i]+p[i+1])/4
            # Every supporting plane participates in the common arrangement.
            # Sorted vertex keys are independent of polygon rotation/winding.
            key=tuple(sorted(set(map(tuple,np.round(polygon,12)))))
            if key in shared:
                f=shared[key];old=all_faces[f]
                if np.max(abs((old.centroid_m-center)/scale))>64*np.finfo(float).eps:
                    raise ValueError('unresolved distinct faces share a quantized geometry key')
                if old.neighbor>=0 or np.linalg.norm((old.area_vector_m2+av)/(np.prod(scale)/scale))>1e-10:
                    raise ValueError('nonmanifold or inconsistent shared face')
                all_faces[f]=CutFace(old.vertices_m,old.area_vector_m2,old.centroid_m,old.owner,owner,old.boundary)
            else:
                shared[key]=len(all_faces);all_faces.append(CutFace(p,av,center,owner,-1,label))
        idx=background[owner];base=np.prod([axes[a][i+1]-axes[a][i] for a,i in enumerate(idx)])
        if not np.isfinite(volume) or volume<=0 or volume/base<1e-13:
            raise ValueError('unresolved region sliver; refine or change geometry')
        volumes.append(float(volume));centers.append(np.asarray(moment/volume,float))
    return CutCellMesh(np.array(volumes),np.array(centers).reshape(-1,3),
        np.array(background,int).reshape(-1,3),tuple(all_faces),np.array(labels))
