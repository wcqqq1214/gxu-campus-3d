"""Fixed-position checks for estimated civil platform parts in source/base/near.

Expected values are independent of the production override. These are adopted
photo-constrained estimates, not measured heights or whole-building acceptance.
"""
import bpy, sys, json, re, hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[1]
TARGET = next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')), ROOT)
PREFIX = next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')), 's2-civil-platform')
ID, CHUNK, Z = 'way/957404988', 'chunk-n2-n3', -4.76
INSET_ROOF = '--inset-roof' in sys.argv
NORTH_FACADE = '--north-facade' in sys.argv
ROOF_VOLUMES = '--roof-volumes' in sys.argv
EAST_SLIT = '--east-slit' in sys.argv

def root_name(obj):
    while obj.parent:
        obj = obj.parent
    return re.sub(r'\.\d+$', '', obj.name)


def check(objects, tolerance):
    trees = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        obj.data.calc_loop_triangles()
        triangles = list(obj.data.loop_triangles)
        trees.append((BVHTree.FromPolygons(
            [obj.matrix_world @ v.co for v in obj.data.vertices],
            [tuple(t.vertices) for t in triangles], all_triangles=True),
            [obj.data.materials[t.material_index].name.split('.')[0] for t in triangles]))

    def ray(origin, direction, distance):
        hits = []
        for tree, materials in trees:
            loc, normal, index, length = tree.ray_cast(Vector(origin), Vector(direction), distance)
            if loc is not None:
                hits.append((length, loc, normal, materials[index]))
        return min(hits, key=lambda h: h[0]) if hits else None

    samples = []
    def roof(x, y, height, material, kind):
        hit = ray((x,y,Z+40),(0,0,-1),40)
        assert hit and hit[3] == material, (kind,x,y,'material',hit)
        assert abs(hit[1].z-Z-height) < tolerance, (kind,x,y,height,hit)
        assert hit[2].z > .99, (kind,'roof normal',hit)
        samples.append(dict(kind=kind,position=[x,y],expectedHeight=height,actualHeight=hit[1].z-Z,material=material))
    for x,y,h,mat,kind in [
        (-680,-775,13.2,'blueRoof','hall'),(-710,-780,13.2,'blueRoof','hall'),
        (-660,-765,13.2,'blueRoof','hall'),(-706,-744,10.8,'paleRoof','labs'),
        (-705,-757,10.8,'paleRoof','labs'),(-725,-747,7.2,'paleRoof','foyer'),
        (-726,-738,7.2,'paleRoof','foyer'),(-715,-721,29.7,'paleRoof','office'),
        (-731,-716,29.7,'paleRoof','office'),(-698,-723,29.7,'paleRoof','office')]:
        roof(x,y,h,mat,kind)
    # Both sides of three independent part junctions; no lost slivers or roofs.
    for x,y,h,mat in [(-710,-760.65,13.2,'dark' if INSET_ROOF else 'blueRoof'),(-710,-760.25,10.8,'paleRoof'),
                       (-709,-729.65,10.8,'paleRoof'),(-709,-729.15,29.7,'paleRoof'),
                       (-719.7,-744,7.2,'paleRoof'),(-719.1,-744,10.8,'paleRoof')]:
        roof(x,y,h,mat,'part-junction')
    # Outward-facing hall east and south walls and office north wall.
    for origin,direction,distance in [((-654,-776,Z+5),(-1,0,0),4),
                                       ((-680,-790,Z+6),(0,1,0),4),
                                       ((-716,-711,Z+17),(0,-1,0),4)]:
        hit=ray(origin,direction,distance)
        assert hit and hit[3]=='white' and hit[2].dot(Vector(direction))<-.98,('outer-wall',origin,hit)
        samples.append(dict(kind='outward-white-wall',position=list(hit[1])))
    # Hall upper glazing: first, middle and last estimated two-row strip.
    # The north edge is independent fixed endpoints, not read from the override.
    a=Vector((-695.093802217242,-760.4825800000607,0))
    b=Vector((-656.418777727391,-760.5382399999202,0))
    outward=Vector((-(b-a).y,(b-a).x,0)).normalized()
    for i in (0,10,21):
        p=a.lerp(b,.025+i*.95/22+.0125)
        for h in (8.375,11.125):
            origin=p+outward*2;origin.z=Z+h
            hit=ray(origin,-outward,3)
            assert hit and hit[3]=='glass',('upper-hall-glass',i,h,hit)
            samples.append(dict(kind='upper-hall-glass',strip=i,height=h))
        origin=p+outward*2;origin.z=Z+4
        hit=ray(origin,-outward,3)
        assert hit and hit[3]=='white',('no-lower-generic-window',i,hit)
        samples.append(dict(kind='hall-lower-solid-wall',strip=i))
    # A clearspan is not filled with intermediate generic floor plates.
    for h in (3.3,6.6,9.9):
        assert ray((-682,-774,Z+h-.1),(0,0,1),.2) is None,('hall-floor',h)
        samples.append(dict(kind='clearspan-no-intermediate-floor',height=h))
    if INSET_ROOF:
        # Independent coordinates on the four 1.2 m border strips, their inner
        # transitions and a corner. These are not resolved from roof metadata.
        for x,y in [(-680,-760.99),(-680,-787.60),(-656.95,-775),
                    (-717.25,-775),(-657,-787.5),(-680,-761.55),
                    (-657.45,-775),(-716.80,-775),(-680,-787.05)]:
            roof(x,y,13.2,'dark','hall-inset-border')
        for x,y in [(-680,-762.1),(-680,-786.5),(-658,-775),(-716,-775),
                    (-680,-761.85),(-657.80,-775),(-716.40,-775),(-680,-786.75)]:
            roof(x,y,13.2,'blueRoof','hall-inset-center')
        # Sum all horizontal top triangles at the adopted hall height. Two
        # coplanar overlays can pass closest-hit rays but fail this area check.
        areas={'dark':0.,'blueRoof':0.}
        for obj in objects:
            if obj.type!='MESH':continue
            obj.data.calc_loop_triangles()
            for tri in obj.data.loop_triangles:
                material=obj.data.materials[tri.material_index].name.split('.')[0]
                if material not in areas:continue
                a,b,c=[obj.matrix_world@obj.data.vertices[k].co for k in tri.vertices]
                if all(abs(p.z-Z-13.2)<tolerance for p in (a,b,c)) and all(-720<p.x<-653 and -790<p.y<-759 for p in (a,b,c)):
                    signed=(b-a).cross(c-a).z/2
                    assert signed>0,('inset-top-normal',material,signed)
                    areas[material]+=signed
        assert abs(sum(areas.values())-1693.454)<tolerance*150,('roof area overlap or gap',areas)
        assert 205<areas['dark']<210 and 1483<areas['blueRoof']<1489,('inset color areas',areas)
        samples.append(dict(kind='single-covered-inset-top',areasMeters2=areas))
    if NORTH_FACADE:
        # Fixed original north/east endpoints and adopted dimensions, independent
        # of the override resolver. Probe every north bay and floor, plus piers
        # and the newly solid upper east wall; a sparse generic grid must fail.
        a=Vector((-734.5484823735649,-713.5278039998846,0))
        b=Vector((-695.3913024054572,-713.5723320000095,0))
        u=(b-a).normalized();n=Vector((-u.y,u.x,0))
        bay=((b-a).length-2)/22
        def wall_sample(p,normal,height,material,kind):
            origin=p+normal*2;origin.z=Z+height
            hit=ray(origin,-normal,3)
            assert hit and hit[3]==material,(kind,list(p),height,hit)
            assert hit[2].dot(normal)>.98,(kind,'outward face',hit)
            samples.append(dict(kind=kind,position=list(p)[:2],height=height,material=material))
        for floor in range(9):
            for col in range(22):
                # Offset from vertical mullion and horizontal pane divider.
                p=a+u*(1+(col+.5)*bay+.24)
                wall_sample(p,n,(floor+.56)*3.3+.30,'glass','north-window-grid')
            wall_sample(a+u*.45,n,(floor+.56)*3.3,'white','north-edge-margin')
        for col in (0,7,14,22):
            p=a+u*(1+col*bay)
            for height in (2.,14.,28.):
                wall_sample(p,n,height,'white','north-continuous-pier')
                origin=p+n*2;origin.z=Z+height
                hit=ray(origin,-n,3)
                assert abs((hit[1]-p).dot(n)-.18)<tolerance,('pier depth',col,height,hit)
        # Upper east side of the office only; low-lab section shares edge 14.
        a=Vector((-695.3913024054572,-713.5723320000095,0))
        b=Vector((-695.2908592664412,-729.4103473955927,0))
        u=(b-a).normalized();n=Vector((-u.y,u.x,0))
        for floor in range(1,9):
            for col in range(3):
                wall_sample(a.lerp(b,(col+.5)/3),n,(floor+.56)*3.3,'white','east-upper-solid')
    if EAST_SLIT:
        # Independent adopted east-end endpoints, not production panel metadata.
        # The large white margins must remain solid around the narrow glazing.
        a=Vector((-695.3913024054572,-713.5723320000095,0))
        b=Vector((-695.2908592664412,-729.4103473955927,0))
        u=(b-a).normalized();n=Vector((-u.y,u.x,0))
        for row in range(8):
            height=3.8+(row+.5)*(26.4-3.8)/8
            for t,material,kind in [(.6,'glass','east-slit-glass'),
                                    (.53,'white','east-slit-north-margin'),
                                    (.67,'white','east-slit-south-margin')]:
                p=a.lerp(b,t);origin=p+n*2;origin.z=Z+height
                hit=ray(origin,-n,3)
                assert hit and hit[3]==material,(kind,row,hit)
                assert hit[2].dot(n)>.98,(kind,'outward normal',hit)
                samples.append(dict(kind=kind,row=row,height=height,material=material))
        for height in (3.5,27.):
            p=a.lerp(b,.6);origin=p+n*2;origin.z=Z+height
            hit=ray(origin,-n,3)
            assert hit and hit[3]=='white',('east-slit-upper-lower-margin',height,hit)
            samples.append(dict(kind='east-slit-upper-lower-margin',height=height))
    if ROOF_VOLUMES:
        a=Vector((-734.5484823735649,-713.5278039998846,0))
        b=Vector((-695.3913024054572,-713.5723320000095,0))
        length=(b-a).length;u=(b-a).normalized();v=Vector((u.y,-u.x,0))
        def at(s,d):return a+u*s+v*d
        # Adopted footprints/heights, independent of resolved roof volume data.
        for name,s,d,width,depth,rise in [
                ('north-strip',.455*length,3.2,.73*length,.4,1.1),
                ('south-strip',.455*length,9.2,.73*length,.4,1.1),
                ('west-return',.09*length+.2,6.2,.4,5.6,1.1),
                ('southeast-block',.89*length,12.2,.14*length,3.8,2.6)]:
            p=at(s,d);roof(p.x,p.y,29.7+rise,'white',name+'-top')
            sides=[(u,width/2),(-u,width/2)]
            # The return's short ends meet the strips; test exposed faces only.
            if name!='west-return':sides += [(v,depth/2),(-v,depth/2)]
            for outward,extent in sides:
                face=p+outward*extent;origin=face+outward;origin.z=Z+29.7+rise/2
                hit=ray(origin,-outward,2)
                assert hit and hit[3]=='white' and hit[2].dot(outward)>.98,(name,'side',hit)
                assert abs((hit[1]-face).dot(outward))<tolerance,(name,'side position',hit)
                samples.append(dict(kind=name+'-outward-side',position=list(hit[1])))
        for s,d in [(.455*length,6.2),(.455*length,1.5),(.455*length,12.5),
                    (.86*length,6.2),(.05*length,6.2)]:
            p=at(s,d);roof(p.x,p.y,29.7,'paleRoof','roof-volume-clear-gap')
    return dict(passed=True,rayCount=len(samples),samples=samples,toleranceMeters=tolerance)

report = dict(passed=False, scope='Estimated hall 13.2 m blue roof, labs 10.8 m, foyer 7.2 m, north nine-storey office 29.7 m; fixed junctions, white walls and upper glazing. Entry and remaining facades pending; not whole-building acceptance.')
report['insetRoofChecked']=INSET_ROOF
report['northFacadeChecked']=NORTH_FACADE
report['roofVolumesChecked']=ROOF_VOLUMES
report['eastSlitChecked']=EAST_SLIT
if NORTH_FACADE:
    report['scope']+=' Includes estimated 22-column north grid, continuous white piers and upper solid east end; ground entry, other elevations and roof structures remain pending.'
if ROOF_VOLUMES:
    report['scope']+=' Includes two 1.1 m raised roof strips, west connection and 2.6 m southeast block, with open roof gaps. Roof dimensions and use remain estimates.'
if EAST_SLIT:
    report['scope']+=' Includes the photo-constrained narrow east glazing strip with eight estimated divisions and surrounding solid wall. Ground openings, corner return and use remain unverified.'
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==ID],.006)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'))
    bpy.context.view_layer.update()
    report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==CHUNK],.05)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{CHUNK}.glb'))
    bpy.context.view_layer.update()
    report['near']=check(list(bpy.context.scene.objects),.02)
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f'public/models/{CHUNK}.glb','public/data/buildings.json']}
    report['passed']=True
except Exception as error:
    report['failure']=str(error)
    raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Civil platform:',report['passed'],flush=True)
