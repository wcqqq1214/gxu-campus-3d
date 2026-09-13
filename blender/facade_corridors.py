"""Recess sourced exterior corridors within an ordinary building's footprint."""
import math


def add_corridor(mesh, facade, z, wall, slab, railing, pitched_roof=False):
    """Replace one vertical wall strip; retain ground floor and roof outline.

    The parser verifies the strip is inside its part and avoids other corridors.
    Geometry uses the same floor slabs, railing and rear wall in both LODs.
    """
    a,b=facade['start'],facade['end'];n=facade['normal']
    length=math.dist(a,b);u=[(b[k]-a[k])/length for k in (0,1)]
    rule=facade['rule']['openCorridor'];inset=rule['endInset'];depth=rule['depth']
    h=facade['height'];levels=int(facade['levels']);fh=h/levels;first=rule['firstLevel']
    lo,hi=inset,length-inset
    point=lambda t,d,height:(a[0]+u[0]*t-n[0]*d,a[1]+u[1]*t-n[1]*d,z+height)
    candidates=[]
    for index,face in enumerate(mesh.f):
        vertices=[mesh.v[k] for k in face]
        if len(face)!=4 or min(v[2] for v in vertices)>z+1e-5 or max(v[2] for v in vertices)<z+h-1e-5:
            continue
        if any(abs((v[0]-a[0])*n[0]+(v[1]-a[1])*n[1])>1e-5 for v in vertices):
            continue
        ends=[(v[0]-a[0])*u[0]+(v[1]-a[1])*u[1] for v in vertices]
        if min(ends)<=lo+1e-5 and max(ends)>=hi-1e-5:
            candidates.append((index,min(ends),max(ends),min(v[2] for v in vertices)-z))
    if len(candidates)!=1:
        raise ValueError(f'Corridor must replace one complete wall face, got {len(candidates)}')
    index,start,end,bottom=candidates[0]
    del mesh.f[index];del mesh.m[index]

    def face(points,material=wall):mesh.face([point(*p) for p in points],material)
    def front(t0,t1,z0,z1):
        if t1-t0>1e-6 and z1-z0>1e-6:
            face([(t0,0,z0),(t1,0,z0),(t1,0,z1),(t0,0,z1)])
    front(start,lo,bottom,h);front(hi,end,bottom,h)
    front(lo,hi,bottom,first*fh-.18)
    for level in range(first,levels):
        floor=level*fh;ceiling=(level+1)*fh-.18
        face([(lo,depth,floor),(hi,depth,floor),(hi,depth,ceiling),(lo,depth,ceiling)])
        face([(lo,0,floor),(lo,depth,floor),(lo,depth,ceiling),(lo,0,ceiling)])
        face([(hi,depth,floor),(hi,0,floor),(hi,0,ceiling),(hi,depth,ceiling)])

    def solid(t0,t1,d0,d1,z0,z1,material,top=True,ends=True):
        # Explicit faces avoid adding a second coplanar roof on the last slab.
        p=[(t0,d0,z0),(t1,d0,z0),(t1,d1,z0),(t0,d1,z0),
           (t0,d0,z1),(t1,d0,z1),(t1,d1,z1),(t0,d1,z1)]
        faces=[(3,2,1,0),(0,1,5,4),(2,3,7,6)]
        if ends:faces.extend([(1,2,6,5),(3,0,4,7)])
        if top:faces.append((4,5,6,7))
        for indices in faces:face([p[k] for k in indices],material)

    for level in range(first,levels+1):
        floor=level*fh
        solid(lo,hi,0,depth,floor-.18,floor,slab,top=level<levels or pitched_roof)
        if 0<level<levels:
            if 'balusters' in rule:
                rail=rule['balusters'];width=rail['width']
                solid(lo,hi,0,.18,floor,floor+.12,railing,ends=False)
                solid(lo,hi,0,.18,floor+rule['railHeight']-.1,floor+rule['railHeight'],railing,ends=False)
                count=max(1,math.ceil((hi-lo)/rail['spacing']))
                for i in range(count):
                    t=lo+(hi-lo)*(i+.5)/count
                    solid(t-width/2,t+width/2,0,.14,floor+.12,floor+rule['railHeight']-.1,railing)
            else:
                solid(lo,hi,0,.14,floor,floor+rule['railHeight'],railing,ends=False)
    if 'piers' in rule:
        pier=rule['piers']
        for i in range(pier['bays']+1):
            t=lo+(hi-lo)*i/pier['bays']
            solid(t-pier['width']/2,t+pier['width']/2,0,pier['depth'],max(bottom,first*fh-.18),h,wall)
