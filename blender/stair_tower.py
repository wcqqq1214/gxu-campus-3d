"""Open return flights, curved mapped landings and level bridges; shared by LODs."""
import math
from geometry import Mesh


def stair_access_door(mesh,door,z,C):
    a=math.radians(door['bearing']);nx,ny=math.sin(a),math.cos(a);x,y=door['center'];w=door['width'];h=door['height'];floor=z+door['floor']
    mesh.box(x+nx*.08,y+ny*.08,floor+h/2,w,.12,h,C['glass'],-a)
    for offset in [-w/2,0,w/2]:mesh.box(x+ny*offset+nx*.16,y-nx*offset+ny*.16,floor+h/2,.055,.08,h,C['dark'],-a)
    for zz in [floor,floor+h]:mesh.box(x+nx*.16,y+ny*.16,zz,w,.08,.055,C['dark'],-a)


def stair_tower_model(b,z,C):
    s=b['form']['stairTower'];c=s['config'];angle=s['angle'];cs,sn=math.cos(angle),math.sin(angle);ox,oy=s['origin']
    def world(p):return (ox+p[0]*cs-p[1]*sn,oy+p[0]*sn+p[1]*cs,z+p[2])
    body=Mesh();roof=Mesh();access=Mesh()
    def face(mesh,points,mat):mesh.face([world(p) for p in points],mat)
    def slab(mesh,shape,top,depth,mat):
        for poly,ts in zip(shape['polygons'],shape['triangles']):
            flat=[p for ring in poly for p in ring[:-1]]
            for i in range(0,len(ts),3):
                face(mesh,[(*flat[k],top) for k in ts[i:i+3]],mat)
                face(mesh,[(*flat[k],top-depth) for k in reversed(ts[i:i+3])],mat)
            for ring in poly:
                for a,b in zip(ring,ring[1:]):face(mesh,[(*a,top-depth),(*b,top-depth),(*b,top),(*a,top)],mat)
    def wall(a,b,low0,low1):
        length=math.dist(a,b)
        if length<1e-6:return
        # Inward offset keeps landings and railings inside their actual polygon.
        nx,ny=-(b[1]-a[1])/length,(b[0]-a[0])/length;t=c['parapetThickness']
        aa=[a[0]+nx*t,a[1]+ny*t];bb=[b[0]+nx*t,b[1]+ny*t];h=c['parapetHeight']
        for lo,hi,mat in [(0,h*.72,C['white']),(h*.72,h*.84,C['pink']),(h*.84,h,C['white'])]:
            p=[(*a,low0+lo),(*b,low1+lo),(*bb,low1+lo),(*aa,low0+lo),(*a,low0+hi),(*b,low1+hi),(*bb,low1+hi),(*aa,low0+hi)]
            for ids in [(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]:face(body,[p[i] for i in ids],mat)
    cut=c['landingCut'];well=c['wellWidth'];width=c['flightWidth'];depth=c['slabThickness'];base=c['baseHeight'];gap=s['floorHeight'];levels=int(b['levels'])
    lanes=[(well/2,well/2+width),(-well/2-width,-well/2)]
    def rails(shape,level,sign,top_floor=False):
        for poly in shape['polygons']:
            for ring in poly:
                for a,b in zip(ring,ring[1:]):
                    if abs(a[1]-s['hostDistance'])<1e-6 and abs(b[1]-s['hostDistance'])<1e-6:continue
                    if abs(a[1]-sign*cut)<1e-6 and abs(b[1]-sign*cut)<1e-6:
                        # Flight mouths remain open; close the unused up-flight
                        # at the final landing instead of leaving a fall opening.
                        openings=lanes[1:] if top_floor else lanes
                        values=sorted({a[0],b[0],*[x for pair in openings for x in pair if min(a[0],b[0])<x<max(a[0],b[0])]})
                        if a[0]>b[0]:values.reverse()
                        for x0,x1 in zip(values,values[1:]):
                            if any(lo<(x0+x1)/2<hi for lo,hi in openings):continue
                            wall([x0,a[1]],[x1,a[1]],level,level)
                    else:wall(a,b,level,level)
    slab(access,s['ground'],base,base+.3,C['stone'])
    for level in range(1,levels):
        h=base+level*gap;slab(body,s['north'],h,depth,C['white']);rails(s['north'],h,1,level==levels-1)
    for level in range(levels-1):
        h=base+(level+.5)*gap;slab(body,s['south'],h,depth,C['white']);rails(s['south'],h,-1)
        for index,(x0,x1) in enumerate(lanes):
            y0,y1=(cut,-cut) if index==0 else (-cut,cut)
            low=base+(level+index*.5)*gap;high=low+gap/2;steps=c['risersPerFlight'];profile=[(y0,low)]
            def oriented(points,mat,reverse=False):face(body,list(reversed(points)) if reverse else points,mat)
            for i in range(steps):
                a=y0+(y1-y0)*i/steps;b1=y0+(y1-y0)*(i+1)/steps;h=low+(high-low)*(i+1)/steps;prior=low+(high-low)*i/steps
                oriented([(x0,a,h),(x1,a,h),(x1,b1,h),(x0,b1,h)],C['stone'],y1<y0)
                oriented([(x0,a,prior),(x1,a,prior),(x1,a,h),(x0,a,h)],C['white'],y1<y0)
                profile.extend([(a,h),(b1,h)])
            oriented([(x0,y0,low-depth),(x0,y1,high-depth),(x1,y1,high-depth),(x1,y0,low-depth)],C['white'],y1<y0)
            oriented([(x0,y0,low-depth),(x1,y0,low-depth),(x1,y0,low),(x0,y0,low)],C['white'],y1<y0)
            oriented([(x0,y1,high-depth),(x1,y1,high-depth),(x1,y1,high),(x0,y1,high)],C['white'],y1>y0)
            for x in [x0,x1]:oriented([(x,y,h) for y,h in profile]+[(x,y1,high-depth),(x,y0,low-depth)],C['white'],(x==x1)==(y1>y0))
            # Winding on the two boundaries places the wall thickness inside the lane.
            if y1>y0:
                wall([x1,y0],[x1,y1],low,high);wall([x0,y1],[x0,y0],high,low)
            else:
                wall([x0,y0],[x0,y1],low,high);wall([x1,y1],[x1,y0],high,low)
    roof_top=b['height'];slab(roof,s['roof'],roof_top,c['roofThickness'],C['white'])
    for p in c['columns']:
        x,y=p['center'];top=roof_top-c['roofThickness'] if p['top']=='roof' else base+(levels-1)*gap-depth
        point=world((x,y,(base+top)/2));body.box(*point,p['width'],p['width'],top-base,C['white'],angle)
    result=Mesh();result.add_part('01_主体轮廓',body);result.add_part('02_屋顶轮廓',roof);result.add_part('03_入口与平台',access)
    return result
