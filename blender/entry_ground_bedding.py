"""Seat entrance paving on soil and feather only its exposed lawn edges.

The road-facing edges retain their prepared road elevations. Raised walks
and lightwells keep their separate grading surfaces and retaining walls.
"""
import math
from geometry import Mesh
from site_geometry import mesh_triangles, split_convex
from shore_geometry import bounds, overlaps, triangles_into


def bed_forecourt(terrain, entry, elevation, material):
    return _grade_forecourt(terrain,entry,elevation,material,road_contact=False)


def grade_rear_road_contact(roads, entry, elevation):
    """Meet the prepared parking grade without changing the road footprint."""
    return _grade_forecourt(roads,entry,elevation,None,road_contact=True)


def _grade_forecourt(terrain, entry, elevation, material, *, road_contact):
    p=entry['recessedStairEntry'];patches=p['landscape']['groundPatches']
    by_id={q['id']:q for q in patches}
    required={'outer-plaza','north-parking','south-parking','south-access'}
    if not required.issubset(by_id):return terrain,{'beddingFaces':0}
    angle=math.radians(entry['bearing']);nx,ny=math.sin(angle),math.cos(angle);x,y=entry['center']
    def local(v):return ((v[0]-x)*ny-(v[1]-y)*nx,-(v[0]-x)*nx-(v[1]-y)*ny)
    def world(w,d,h):return (x+ny*w-nx*d,y-nx*w-ny*d,elevation+h)
    def ccw(points):
        if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))<0:points=list(reversed(points))
        return points
    patches=list(patches)
    # The low, level strip at the first riser is part of the same soil bed.
    w=p['apronFrontWidth']/2;start=p['apronStart'];end=p['landscape']['lowerFlight']['toe'];h=p['landscape']['lowerFlight']['baseHeight']
    patches.append(dict(boundary=[[-w,start],[w,start],[w,end],[-w,end],[-w,start]],
                        vertices=[[-w,start,h],[w,start,h],[w,end,h],[-w,end,h]],triangles=[0,1,2,0,2,3]))
    masks=[];bedding=Mesh();samples=[]
    for patch in patches:
        ring=ccw([world(w,d,0) for w,d in patch['boundary'][:-1]])
        if not road_contact:masks.append((ring,bounds(ring)))
        vs=patch['vertices'];ids=patch['triangles']
        for i in range(0,len(ids),3):
            tri=[vs[k] for k in ids[i:i+3]];samples.append(tri)
            if not road_contact:bedding.face(ccw([world(w,d,h-.04) for w,d,h in tri]),material)
    def finish(w,d,extend_to=None):
        for a,b,c in samples:
            den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(den)<1e-10:continue
            u=((b[1]-c[1])*(w-c[0])+(c[0]-b[0])*(d-c[1]))/den
            v=((c[1]-a[1])*(w-c[0])+(a[0]-c[0])*(d-c[1]))/den
            if min(u,v,1-u-v)>=-1e-6:
                if extend_to is not None:
                    w,d=extend_to
                    u=((b[1]-c[1])*(w-c[0])+(c[0]-b[0])*(d-c[1]))/den
                    v=((c[1]-a[1])*(w-c[0])+(a[0]-c[0])*(d-c[1]))/den
                return u*a[2]+v*b[2]+(1-u-v)*c[2]-(.015 if road_contact else .04)
        raise ValueError('Soil transition has no paving edge')
    plaza=by_id['outer-plaza']['boundary']
    lo,hi=min(v[0] for v in plaza),max(v[0] for v in plaza);front=min(v[1] for v in plaza)
    parking_front=min(v[1] for v in by_id['north-parking']['boundary']);width=1.5
    north=min(v[0] for v in by_id['north-parking']['boundary']);south=max(v[0] for v in by_id['south-access']['boundary'])
    inner=[(north,parking_front),(lo,parking_front),(lo,front),(hi,front),(hi,parking_front),(south,parking_front)]
    outer=[(north,parking_front-width),(lo-width,parking_front-width),(lo-width,front-width),(hi+width,front-width),(hi+width,parking_front-width),(south,parking_front-width)]
    bands=[]
    if not road_contact:
        for i in range(len(inner)-1):bands.append((inner[i],inner[i+1],outer[i+1],outer[i],width,False))
    for name in ('north-parking','south-parking','south-access'):
        ring=by_id[name]['boundary'];back=max(v[1] for v in ring);ws=[v[0] for v in ring if abs(v[1]-back)<1e-6]
        a,b=(min(ws),back),(max(ws),back);width=1.5
        bands.append((a,b,(b[0],back+width),(a[0],back+width),width,True))
    transition=[]
    for a,b,c,d,width,rear in bands:
        if rear:
            # Keep the accepted 30 cm shoulder on the paving's own plane.
            # Explicit stations make this independent of the DEM triangle size
            # and of previously edited preview terrain. Beyond the shoulder,
            # smoothstep returns to the original ground within the same 1.5 m.
            stations=sorted({a[0],b[0]}|{v[0] for patch in patches for v in patch['vertices']
                if abs(v[1]-a[1])<1e-6 and a[0]<v[0]<b[0]})
            rings=[[(w0,a[1]+s0),(w1,a[1]+s0),(w1,a[1]+s1),(w0,a[1]+s1)]
                for w0,w1 in zip(stations,stations[1:])
                for s0,s1 in zip((0,.3,.6,.9,1.2),(.3,.6,.9,1.2,1.5))]
        else:rings=[(a,b,c,d)]
        for points in rings:
            ring=ccw([world(*v,0) for v in points])
            transition.append((ring,bounds(ring),a,b,width,rear))
    area=bounds([v for ring,_ in masks for v in ring]+[v for ring,*_ in transition for v in ring])
    selected={i for i,f in enumerate(terrain.f) if overlaps(bounds([terrain.v[k] for k in f]),area)}
    result=Mesh()
    for i,f in enumerate(terrain.f):
        if i not in selected:result.face([terrain.v[k] for k in f],terrain.m[i])
    for ids,fi in mesh_triangles(terrain):
        if fi not in selected:continue
        remaining=[[terrain.v[k] for k in ids]]
        for ring,bb in masks:
            parts=[]
            for part in remaining:
                if not overlaps(bounds(part),bb):parts.append(part);continue
                _,outside=split_convex(part,ring);parts.extend(outside)
            remaining=parts
        for ring,bb,a,b,width,rear in transition:
            parts=[];dx,dy=b[0]-a[0],b[1]-a[1];length2=dx*dx+dy*dy
            for part in remaining:
                if not overlaps(bounds(part),bb):parts.append(part);continue
                kept,outside=split_convex(part,ring);parts.extend(outside)
                blend=[]
                for q in kept:
                    w,d=local(q);t=max(0,min(1,((w-a[0])*dx+(d-a[1])*dy)/length2));qw,qd=a[0]+t*dx,a[1]+t*dy
                    distance=math.hypot(w-qw,d-qd)
                    if rear:
                        t=max(0,min(1,(distance-.3)/(width-.3)));weight=t*t*(3-2*t)
                        bed_height=finish(qw,qd,extend_to=(w,d))
                    else:
                        weight=min(1,distance/width);bed_height=finish(qw,qd)
                    height=q[2]*weight+(elevation+bed_height)*(1-weight)
                    blend.append((q[0],q[1],height))
                triangles_into(result,blend,terrain.m[fi])
            remaining=parts
        for part in remaining:triangles_into(result,part,terrain.m[fi])
    result.extend(bedding)
    if road_contact:return result,{'rearContactClearanceMeters':.015,'rearShoulderMeters':.3,'rearFeatherMeters':1.5}
    return result,{'beddingFaces':len(bedding.f),'lawnFeatherMeters':1.5,'edgeClearanceMeters':.04}
