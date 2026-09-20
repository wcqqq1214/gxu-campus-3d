"""Recolour one complete exterior wall without adding a coplanar overlay."""
import math


def apply_wall_finish(mesh, facade, z, material):
    a,b=facade['start'],facade['end'];n=facade['normal'];length=math.dist(a,b)
    u=[(b[k]-a[k])/length for k in (0,1)];matches=[]
    for i,face in enumerate(mesh.f):
        vertices=[mesh.v[k] for k in face]
        if len(face)!=4 or abs(min(v[2] for v in vertices)-(z-.5))>1e-5 or abs(max(v[2] for v in vertices)-(z+facade['height']))>1e-5:
            continue
        if any(abs((v[0]-a[0])*n[0]+(v[1]-a[1])*n[1])>1e-5 for v in vertices):
            continue
        along=[(v[0]-a[0])*u[0]+(v[1]-a[1])*u[1] for v in vertices]
        if abs(min(along))<1e-5 and abs(max(along)-length)<1e-5:matches.append(i)
    if len(matches)!=1:
        raise ValueError(f'Wall finish must match exactly one complete wall, got {len(matches)}')
    mesh.m[matches[0]]=material
