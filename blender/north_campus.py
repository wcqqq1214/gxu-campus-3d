"""Northern campus building dispatch and site geometry."""
import math
from geometry import Mesh
from north_campus_architecture import building_model


def site_models(data, colors, elevation):
    roads, sports = Mesh(), Mesh()
    for item in data['grounds']:
        mesh = sports if item['kind']=='sports' else roads
        vertices, triangles = item['vertices'], item['triangles']
        for i in range(0,len(triangles),3):
            mesh.face([(vertices[k][0],vertices[k][1],elevation(*vertices[k])+.14)
                       for k in triangles[i:i+3]],colors[item['material']])
    track = data['track']
    x, y = track['center']
    # Image Y grows south, hence the negative rotation in campus coordinates.
    angle = -math.radians(track['rotationDegrees'])
    ca, sa = math.cos(angle), math.sin(angle)
    radius = track['depth']/2
    straight = max(0,track['width']/2-radius)

    # A playing field is planar. Coarse DEM has ~2 m of artificial relief here;
    # use a conservative raised display grade and a sloped apron, not a warped
    # field whose independently triangulated markings flicker through the turf.
    level=max(elevation(x+u*ca-v*sa,y+u*sa+v*ca)
              for u in (-track['width']/2,0,track['width']/2)
              for v in (-radius,0,radius))+.2

    def point(u,v,offset=.2):
        px,py = x+u*ca-v*sa,y+u*sa+v*ca
        return (px,py,level+offset)

    def loop(r):
        return [(side*straight+r*math.cos(t),r*math.sin(t))
                for side,start in [(1,-math.pi/2),(-1,math.pi/2)]
                for t in [start+math.pi*i/24 for i in range(25)]]

    def band(r1,r2,material,offset=.22):
        a,b=loop(r1),loop(r2)
        for i in range(len(a)):
            j=(i+1)%len(a)
            sports.face([point(*p,offset) for p in [a[i],a[j],b[j],b[i]]],colors[material])
    inner = radius-5
    outer,apron=loop(radius+.12),loop(radius+2)
    for i in range(len(outer)):
        j=(i+1)%len(outer)
        a,b=point(*apron[i]),point(*apron[j])
        sports.face([point(*outer[i]),point(*outer[j]),
                     (b[0],b[1],elevation(b[0],b[1])+.14),
                     (a[0],a[1],elevation(a[0],a[1])+.14)],colors['trackApron'])
    band(radius,inner,'track')
    for lane in range(track['laneCount']+1):
        r=inner+5*lane/track['laneCount']
        band(r,r+.07,'sportWhite',.25)
    loop_points=loop(inner-.08)
    # The field is planar; one fan avoids redundant concentric subdivisions.
    for i,a in enumerate(loop_points):
        b=loop_points[(i+1)%len(loop_points)]
        sports.face([point(0,0),point(*a),point(*b)],colors['pitch'])
    def paint(a,b):
        length=math.dist(a,b)
        nx,ny=-(b[1]-a[1])/length*.065,(b[0]-a[0])/length*.065
        sports.face([point(a[0]-nx,a[1]-ny,.27),point(b[0]-nx,b[1]-ny,.27),
                     point(b[0]+nx,b[1]+ny,.27),point(a[0]+nx,a[1]+ny,.27)],colors['sportWhite'])
    sx,sy=straight+inner*.45,inner*.72
    corners=[(-sx,-sy),(sx,-sy),(sx,sy),(-sx,sy)]
    for a,b in zip(corners,corners[1:]+corners[:1]):paint(a,b)
    paint((0,-sy),(0,sy))
    for i in range(48):
        a,b=i*math.tau/48,(i+1)*math.tau/48
        paint((5*math.cos(a),5*math.sin(a)),(5*math.cos(b),5*math.sin(b)))
    if data.get('underpass'):
        from north_underpass import underpass_model
        roads.extend(underpass_model(data['underpass'],colors,elevation))
    return {'north-campus-roads':roads,'north-campus-sports':sports}
