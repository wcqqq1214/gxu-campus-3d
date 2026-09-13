"""Connect an ordinary entrance sideways or forward to an actual road plane."""
import bisect,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from geometry import Mesh
from site_geometry import mesh_triangles,split_convex,contact_road
from paving_geometry import clear_paving_ground
from shore_geometry import conform_edges,bounds,overlaps

def build_side_connection(site,C,elevation,terrain,roads):
    angle=site['angle'];cs,sn=math.cos(angle),math.sin(angle);ox,oy=site['origin']
    def world(x,y):return ox+x*cs-y*sn,oy+x*sn+y*cs
    origin_z=elevation(*site['buildingCenter'])+site['stairBaseHeight']
    front=site.get('type')=='front-connection'
    columns=site['columns'];ys=[p[0] if front else p[1] for p in columns]
    half=site['entry']['stairFlight' if front else 'attachedPortico']['width']/2
    road=BVHTree.FromPolygons(roads.v,[ids for ids,_ in mesh_triangles(roads)],all_triangles=True)
    ground=BVHTree.FromPolygons(terrain.v,[ids for ids,_ in mesh_triangles(terrain)],all_triangles=True)
    heights=[]
    for x,y in columns:
        wx,wy=world(x,y);qx,qy=world(x,y+.025) if front else world(x-.025,y)
        hit,normal,_,_=road.ray_cast(Vector((qx,qy,origin_z+100)),Vector((0,0,-1)),200)
        if hit is None or abs(normal.z)<.5:raise ValueError('No road plane at side connection')
        heights.append(hit.z+(normal.x*(hit.x-wx)+normal.y*(hit.y-wy))/normal.z)
    def road_end(y):
        y=max(ys[0],min(ys[-1],y));i=min(len(ys)-2,max(0,bisect.bisect_right(ys,y)-1));t=(y-ys[i])/(ys[i+1]-ys[i])
        axis=1 if front else 0
        return columns[i][axis]*(1-t)+columns[i+1][axis]*t,heights[i]*(1-t)+heights[i+1]*t
    def point(x,y):
        if front:
            end,h=road_end(x);t=min(1,max(0,(y-site['startY'])/(end-site['startY'])))
        else:
            end,h=road_end(y);lead=min(site['leadDistance'],max(0,y-site['startY']))
            t=min(1,max(0,(max(0,-x-half)+lead)/(-end-half+lead)))
        wx,wy=world(x,y);return wx,wy,origin_z+(h-origin_z)*t
    surface=Mesh();step=site['meshStep'];vs=site['localMesh']['vertices'];ts=site['localMesh']['triangles']
    for i in range(0,len(ts),3):
        tri=[(*vs[k],0) for k in ts[i:i+3]]
        if (tri[1][0]-tri[0][0])*(tri[2][1]-tri[0][1])-(tri[1][1]-tri[0][1])*(tri[2][0]-tri[0][0])<0:tri.reverse()
        for ix in range(math.floor(min(p[0] for p in tri)/step),math.ceil(max(p[0] for p in tri)/step)):
            for iy in range(math.floor(min(p[1] for p in tri)/step),math.ceil(max(p[1] for p in tri)/step)):
                x,y=ix*step,iy*step;piece,_=split_convex(tri,[(x,y),(x+step,y),(x+step,y+step),(x,y+step)])
                for j in range(1,len(piece)-1):
                    a,b,c=piece[0],piece[j],piece[j+1]
                    if abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))>1e-9:surface.face([point(*p[:2]) for p in [a,b,c]],C[site['material']])
    # The same exact plane clipping used for ordinary paving lowers terrain
    # only beneath the connector; no campus-wide mesh resampling is needed.
    terrain,repair=clear_paving_ground(terrain,surface,{'bounds':site['gradingBounds'],'groundClearance':site['groundClearance']})
    sides=Mesh();ring=site['localPolygon']
    for a,b in zip(ring,ring[1:]):
        # Leave both real connections open: staircase base and mapped footway.
        if abs(a[1]-site['startY'])<1e-6 and abs(b[1]-site['startY'])<1e-6:continue
        if front:
            if abs(a[1]-road_end(a[0])[0])<1e-6 and abs(b[1]-road_end(b[0])[0])<1e-6:continue
        elif abs(a[0]-road_end(a[1])[0])<1e-6 and abs(b[0]-road_end(b[1])[0])<1e-6:continue
        count=max(1,math.ceil(math.dist(a,b)/step));stations=[]
        for j in range(count+1):
            t=j/count;p=point(a[0]*(1-t)+b[0]*t,a[1]*(1-t)+b[1]*t)
            hit=ground.ray_cast(Vector((p[0],p[1],origin_z+100)),Vector((0,0,-1)),200)[0]
            if hit is None:raise ValueError('Missing connector edge ground')
            stations.append((p,(p[0],p[1],min(p[2],hit.z)-site['groundClearance'])))
        for a,b in zip(stations,stations[1:]):sides.face([a[1],b[1],b[0],a[0]],C[site['material']])
    def contact_outline(extra):
        lo=ys[0]-site['roadContactSideMargin']-extra;hi=ys[-1]+site['roadContactSideMargin']+extra
        if front:
            slope=(columns[-1][1]-columns[0][1])/(ys[-1]-ys[0])
            def edge(x):return columns[0][1]+(x-ys[0])*slope
            return [world(lo,edge(lo)-.05-extra),world(hi,edge(hi)-.05-extra),world(hi,edge(hi)+site['roadContactDepth']+extra),world(lo,edge(lo)+site['roadContactDepth']+extra)]
        slope=(columns[-1][0]-columns[0][0])/(ys[-1]-ys[0])
        def edge(y):return columns[0][0]+(y-ys[0])*slope
        return [world(edge(lo)-site['roadContactDepth']-extra,lo),world(edge(lo)+.05+extra,lo),world(edge(hi)+.05+extra,hi),world(edge(hi)-site['roadContactDepth']-extra,hi)]
    road_triangles=mesh_triangles(roads);outer=contact_outline(site['joinOverlap']);contact_bounds=bounds(outer)
    touched=[roads.v[k] for ids,_ in road_triangles if overlaps(bounds([roads.v[k] for k in ids]),contact_bounds) for k in ids]
    roads,contact=contact_road(roads,road_triangles,contact_outline(0),outer,site['joinOverlap'],site['groundClearance'])
    # Clipping introduces vertices on retained long road edges. Split their
    # incident triangles too, or campus-wide Draco quantization opens cracks
    # beyond the small contact node even when the source planes coincide.
    if touched:
        area=[v+(-1 if i<2 else 1) for i,v in enumerate(bounds(touched))]
        roads=conform_edges(roads,area);contact=conform_edges(contact,area)
    mesh=Mesh();mesh.add_part('01_入口直向铺地' if front else '01_入口转向铺地',surface);mesh.add_part('02_铺地侧面收口',sides);mesh.add_part('03_人行道接口原铺面',contact)
    # Contact aprons continue the original horizontal road texture even
    # where their buried lip or a thin float32 face has a steep normal.
    mesh.xy_uv_materials=set(contact.m)
    return terrain,roads,{'site-'+site['id']:mesh},[{'id':site['id'],'stairBaseElevation':origin_z,'roadEdgeElevations':heights,'pavingFaces':len(surface.f),'sideFaces':len(sides.f),'groundRepair':repair,'dimensionsEstimated':True}]
