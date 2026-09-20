"""Recess sourced exterior corridors within an ordinary building's footprint."""
import math


def add_corridor_openings(mesh, facade, z, C):
    """Place explicit doors/windows on ground wall or recessed upper back wall."""
    rule = facade['rule']['openCorridor']
    a, b = facade['start'], facade['end']
    length = math.dist(a, b)
    u = [(b[k]-a[k])/length for k in (0, 1)]
    n = facade['normal']; theta = math.atan2(u[1], u[0])
    fh = facade['height']/facade['levels']
    for opening in rule.get('openings', []):
        for level in opening['levels']:
            depth = rule['depth'] if rule['firstLevel'] <= level <= rule.get('lastLevel',facade['levels']-1) else 0
            x, y = [a[k]+(b[k]-a[k])*opening['t']-n[k]*depth for k in (0, 1)]
            width, height = opening['width'], opening['height']
            floor = z+level*fh+opening['sill']
            mesh.box(x+n[0]*.10,y+n[1]*.10,floor+height/2,width,.08,height,C['glass'],theta)
            material = C['dark' if opening['kind']=='door' else 'white']
            for t in (-width/2, width/2):
                mesh.box(x+u[0]*t+n[0]*.16,y+u[1]*t+n[1]*.16,floor+height/2,.06,.08,height,material,theta)
            for h in (floor, floor+height):
                mesh.box(x+n[0]*.16,y+n[1]*.16,h,width+.06,.08,.06,material,theta)
            if opening['kind']=='window':
                mesh.box(x+n[0]*.17,y+n[1]*.17,floor+height/2,width,.04,.04,material,theta)


def add_corridor(mesh, facade, z, wall, slab, railing, pitched_roof=False):
    """Replace one vertical wall strip; retain ground floor and roof outline.

    The parser verifies the strip is inside its part and avoids other corridors.
    Geometry uses the same floor slabs, railing and rear wall in both LODs.
    """
    a,b=facade['start'],facade['end'];n=facade['normal']
    length=math.dist(a,b);u=[(b[k]-a[k])/length for k in (0,1)]
    rule=facade['rule']['openCorridor'];inset=rule['endInset'];depth=rule['depth']
    h=facade['height'];levels=int(facade['levels']);fh=h/levels;first=rule['firstLevel']
    last=rule.get('lastLevel',levels-1)
    corridor_top=h if last==levels-1 else (last+1)*fh
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

    # Exterior rings may run either way. The local (t, inward depth) frame
    # must have positive XY handedness for the face templates below.
    reverse = u[1]*n[0]-u[0]*n[1] < 0
    def face(points,material=wall):
        mesh.face([point(*p) for p in (reversed(points) if reverse else points)],material)
    def front(t0,t1,z0,z1):
        if t1-t0>1e-6 and z1-z0>1e-6:
            face([(t0,0,z0),(t1,0,z0),(t1,0,z1),(t0,0,z1)])
    front(start,lo,bottom,h);front(hi,end,bottom,h)
    front(lo,hi,bottom,first*fh-rule.get('firstSlabThickness',.18))
    front(lo,hi,corridor_top,h)
    for level in range(first,last+1):
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

    for level in range(first,last+2):
        floor=level*fh
        thickness=rule.get('firstSlabThickness',.18) if level==first else .18
        solid(lo,hi,0,depth,floor-thickness,floor,slab,top=level<=last or (last==levels-1 and pitched_roof))
        if 0<level<=last:
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
        pier_first=pier.get('firstLevel',first)
        pier_slab=rule.get('firstSlabThickness',.18) if pier_first==first else .18
        for i in range(pier['bays']+1):
            t=lo+(hi-lo)*i/pier['bays']
            solid(t-pier['width']/2,t+pier['width']/2,0,pier['depth'],max(bottom,pier_first*fh-pier_slab),corridor_top,wall)
