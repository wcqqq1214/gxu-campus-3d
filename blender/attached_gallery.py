"""Enclosed lower storey, upper gallery and a sloping roof extension."""
import math


def add_attached_gallery(mesh, facade, z, wall, C):
    p = facade['attachedGallery']; a, b, n = facade['start'], facade['end'], facade['normal']
    length = math.dist(a, b); u = [(b[k]-a[k])/length for k in (0, 1)]
    lo, hi, depth, floor = p['endInset'], length-p['endInset'], p['depth'], p['floorHeight']
    angle = math.atan2(u[1], u[0])
    def point(t, d, h):
        f=(t-lo)/(hi-lo)
        outer=p.get('outerOffsets',[lo,hi])
        t+=((outer[0]-lo)*(1-f)+(outer[1]-hi)*f)*d/depth
        return (a[0]+u[0]*t+n[0]*d, a[1]+u[1]*t+n[1]*d, z+h)
    def face(points, material):
        mesh.face([point(*v) for v in points], material)
    def box(t, d, bottom, top, width, thickness, material):
        x, y, height = point(t, d, (bottom+top)/2)
        mesh.box(x, y, height, width, thickness, top-bottom, material, angle)
    # The old rear wall becomes an internal lower-storey partition; do not
    # generate duplicate lower windows there. New front and side returns
    # extend below the datum and meet the existing wall along the rear edge.
    face([(lo,0,-.5),(lo,depth,-.5),(hi,depth,-.5),(hi,0,-.5)], wall)
    face([(lo,depth,-.5),(hi,depth,-.5),(hi,depth,floor-p['slabThickness']),(lo,depth,floor-p['slabThickness'])], wall)
    face([(lo,0,-.5),(lo,depth,-.5),(lo,depth,floor),(lo,0,floor)], wall)
    face([(hi,depth,-.5),(hi,0,-.5),(hi,0,floor),(hi,depth,floor)], wall)
    for points in [
        [(lo,0,floor),(hi,0,floor),(hi,depth,floor),(lo,depth,floor)],
        [(lo,depth,floor-p['slabThickness']),(hi,depth,floor-p['slabThickness']),(hi,0,floor-p['slabThickness']),(lo,0,floor-p['slabThickness'])],
        [(lo,depth,floor-p['slabThickness']),(hi,depth,floor-p['slabThickness']),(hi,depth,floor),(lo,depth,floor)]]:
        face(points,C['white'])
    def railing(t0, t1, d0, d1):
        distance = math.hypot(t1-t0, d1-d0); count = math.ceil(distance/p['balusterSpacing'])
        start,end=point(t0,d0,0),point(t1,d1,0)
        distance=math.dist(start,end);rail_angle=math.atan2(end[1]-start[1],end[0]-start[0])
        def beam(bottom, top):
            x,y,h=point((t0+t1)/2,(d0+d1)/2,(bottom+top)/2)
            mesh.box(x,y,h,distance,.16,top-bottom,C['white'],rail_angle)
        beam(floor,floor+.12);beam(floor+p['railHeight']-.1,floor+p['railHeight'])
        for i in range(count):
            f=(i+.5)/count
            box(t0+(t1-t0)*f,d0+(d1-d0)*f,floor+.12,floor+p['railHeight']-.1,
                p['balusterWidth'],p['balusterWidth'],C['white'])
    railing(lo,hi,depth-.08,depth-.08)
    if not p.get('boundedEnds'):
        railing(lo+.08,lo+.08,0,depth-.08)
        railing(hi-.08,hi-.08,0,depth-.08)
    h=facade['height']; outer=h-p['roofDrop']; thickness=p['slabThickness']
    face([(lo,0,h),(hi,0,h),(hi,depth,outer),(lo,depth,outer)],C['red'])
    face([(lo,depth,outer-thickness),(hi,depth,outer-thickness),(hi,0,h-thickness),(lo,0,h-thickness)],C['white'])
    for t0,d0,t1,d1,z0,z1 in [(lo,0,lo,depth,h,outer),(hi,depth,hi,0,outer,h),(lo,depth,hi,depth,outer,outer)]:
        face([(t0,d0,z0-thickness),(t1,d1,z1-thickness),(t1,d1,z1),(t0,d0,z0)],C['white'])
    for opening in p['upperOpenings']:
        t=opening['t']*length;bottom=opening['bottom'];top=opening['top'];width=opening['width']
        box(t,.07,bottom,top,width+.14,.12,C['white'])
        box(t,.15,bottom+.07,top-.07,width,.06,C['red'] if opening['kind']=='door' else C['glass'])
        if opening['kind']=='window':
            box(t,.19,bottom+(top-bottom)*.6-.025,bottom+(top-bottom)*.6+.025,width,.04,C['white'])
