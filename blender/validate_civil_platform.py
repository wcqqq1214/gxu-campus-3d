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
LAB_FACADE = '--lab-facade' in sys.argv
REPARTITION = '--repartition' in sys.argv
PORTICO_GLASS = '--portico-glass' in sys.argv
FOYER_PROFILE = '--foyer-profile' in sys.argv
ROOF_RIM = '--roof-rim' in sys.argv
ENTRY_BAY = '--entry-bay' in sys.argv
if ENTRY_BAY and not PORTICO_GLASS:
    raise ValueError('--entry-bay requires --portico-glass')
if ROOF_RIM and not FOYER_PROFILE:
    raise ValueError('--roof-rim requires --foyer-profile')
if FOYER_PROFILE and not REPARTITION:
    raise ValueError('--foyer-profile requires --repartition')
if PORTICO_GLASS and not REPARTITION:
    raise ValueError('--portico-glass requires --repartition')
if REPARTITION and LAB_FACADE:
    raise ValueError('Use --repartition for the corrected north low wing; --lab-facade is historical')

def profile_height(x,y):
    d=(x+698.6939074704767)*(-.9999798907471006)+(y+760.4773988305454)*(-.0063417743114130036)
    knots=[(0.,0.),(5.354095349427889,.2611651689888372),
           (10.708190698855779,.7917047464637365),(16.062286048283667,1.5146394463523694),
           (21.416381397711557,2.4)]
    for (lo,h0),(hi,h1) in zip(knots,knots[1:]):
        if d<=hi+1e-7:return 10.8+h0+(h1-h0)*(d-lo)/(hi-lo)
    raise AssertionError(('profile sample beyond adopted roof',x,y))


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
        assert hit[2].z > (.98 if FOYER_PROFILE and kind in ('foyer-profile','profile-rim') else .99), (kind,'roof normal',hit)
        samples.append(dict(kind=kind,position=[x,y],expectedHeight=height,actualHeight=hit[1].z-Z,material=material))
    roof_samples = [
        (-680,-775,13.2,'blueRoof','hall'),(-710,-780,13.2,'blueRoof','hall'),
        (-660,-765,13.2,'blueRoof','hall'),(-706,-744,10.8,'paleRoof','labs'),
        (-705,-757,10.8,'paleRoof','labs'),(-725,-747,7.2,'paleRoof','foyer'),
        (-726,-738,7.2,'paleRoof','foyer'),(-715,-721,29.7,'paleRoof','office'),
        (-731,-716,29.7,'paleRoof','office'),(-698,-723,29.7,'paleRoof','office')]
    if REPARTITION:
        roof_samples=[v for v in roof_samples if v[4] not in ('labs','hall')] + [
            (-680,-775,13.2,'blueRoof','hall'),(-710,-780,13.2,'blueRoof','hall'),
            (-680,-763,7.2,'paleRoof','north-low-wing'),(-660,-763,7.2,'paleRoof','north-low-wing'),
            (-706,-744,10.8,'paleRoof','link-foyer'),(-696.7,-744,7.2,'paleRoof','link-portico')]
    if FOYER_PROFILE:
        roof_samples=[(x,y,profile_height(x,y),mat,'foyer-profile') if kind=='link-foyer' else (x,y,h,mat,kind) for x,y,h,mat,kind in roof_samples]
    for x,y,h,mat,kind in roof_samples:
        roof(x,y,h,mat,kind)
    # Both sides of three independent part junctions; no lost slivers or roofs.
    seams = [(-710,-760.65,13.2,'dark' if INSET_ROOF else 'blueRoof'),(-710,-760.25,10.8,'paleRoof'),
                       (-709,-729.65,10.8,'paleRoof'),(-709,-729.15,29.7,'paleRoof'),
                       (-719.7,-744,7.2,'paleRoof'),(-719.1,-744,10.8,'paleRoof')]
    if REPARTITION:
        seams=[(-680,-766.9,13.2,'dark'),(-680,-766.1,7.2,'paleRoof'),
               (-706,-729.7,10.8,'paleRoof'),(-706,-729.1,29.7,'paleRoof'),
               (-699.2,-744,10.8,'paleRoof'),(-698.5,-744,7.2,'paleRoof')]
    for x,y,h,mat in seams:
        if FOYER_PROFILE and (x,y) in [(-706,-729.7),(-699.2,-744)]:
            roof(x,y,profile_height(x,y),mat,'foyer-profile')
        else:
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
    if REPARTITION:
        a-=outward*6; b-=outward*6
    for i in (0,10,21):
        p=a.lerp(b,.025+i*.95/22+.0125)
        for h in ((9.2,11.4) if REPARTITION else (8.375,11.125)):
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
            if REPARTITION and y in (-760.99,-761.55):y-=6
            roof(x,y,13.2,'dark','hall-inset-border')
        for x,y in [(-680,-762.1),(-680,-786.5),(-658,-775),(-716,-775),
                    (-680,-761.85),(-657.80,-775),(-716.40,-775),(-680,-786.75)]:
            if REPARTITION and y in (-762.1,-761.85):y-=6
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
        assert abs(sum(areas.values())-(1325.345 if REPARTITION else 1693.454))<tolerance*150,('roof area overlap or gap',areas)
        if REPARTITION:
            assert 190<areas['dark']<196 and 1129<areas['blueRoof']<1135,('repartition inset color areas',areas)
        else:
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
    if LAB_FACADE or REPARTITION:
        # Fixed east-side low-lab segment, separate from the nine-storey office.
        # Adopted grid dimensions are not loaded from production metadata.
        a=Vector((-695.2908592664412,-729.4103473955927,0))
        b=Vector((-695.093802217242,-760.4825800000607,0))
        if REPARTITION:
            a=Vector((-695.093802217242,-760.4825800000607,0))
            b=Vector((-656.418777727391,-760.5382399999202,0))
        u=(b-a).normalized();n=Vector((-u.y,u.x,0));bay=((b-a).length-1.3)/18
        for floor in range(2 if REPARTITION else 3):
            for col in range(18):
                p=a+u*(.65+(col+.5)*bay+.20)
                origin=p+n*2;origin.z=Z+(floor+.56)*3.6+.30
                hit=ray(origin,-n,3)
                assert hit and hit[3]=='glass' and hit[2].dot(n)>.98,(('lab-north-' if REPARTITION else 'lab-east-')+'glass',floor,col,hit)
                samples.append(dict(kind=('lab-north-' if REPARTITION else 'lab-east-')+'glass',floor=floor,column=col))
            for distance in (.25,(b-a).length-.25):
                p=a+u*distance;origin=p+n*2;origin.z=Z+(floor+.56)*3.6
                hit=ray(origin,-n,3)
                assert hit and hit[3]=='white',(('lab-north-' if REPARTITION else 'lab-east-')+'end-margin',floor,distance,hit)
                samples.append(dict(kind=('lab-north-' if REPARTITION else 'lab-east-')+'end-margin',floor=floor,distance=distance))
        for col in (0,6,12,18):
            p=a+u*(.65+col*bay)
            for height in ((1.,5.) if REPARTITION else (1.,5.,9.8)):
                origin=p+n*2;origin.z=Z+height
                hit=ray(origin,-n,3)
                assert hit and hit[3]=='white' and hit[2].dot(n)>.98,(('lab-north-' if REPARTITION else 'lab-east-')+'pier',col,height,hit)
                assert abs((hit[1]-p).dot(n)-.14)<tolerance,(('lab-north-' if REPARTITION else 'lab-east-')+'pier-depth',col,height,hit)
                samples.append(dict(kind=('lab-north-' if REPARTITION else 'lab-east-')+'continuous-pier',column=col,height=height))
    if REPARTITION:
        # Fixed front-edge anchors and six estimated columns. Test both solid
        # supports and the open bays; a replacement window wall must fail.
        a=Vector((-695.2908592664412,-729.4103473955927,0))
        b=Vector((-695.093802217242,-760.4825800000607,0))
        length=(b-a).length;u=(b-a).normalized();n=Vector((-u.y,u.x,0))
        distances = ([2+i*(length-4)/6 for i in (0,1,3,4,5,6)] if ENTRY_BAY
                     else [2+i*(length-4)/5 for i in range(6)])
        for i, distance in enumerate(distances):
            p=a+u*distance
            origin=p+n*2;origin.z=Z+3.2
            hit=ray(origin,-n,6)
            assert hit and hit[3]=='white' and abs(hit[0]-2.675)<tolerance*2,('portico-column',i,hit)
            samples.append(dict(kind='portico-column',column=i,distance=hit[0]))
        for i in range(5):
            p=a+u*((distances[i]+distances[i+1])/2)
            origin=p+n*2;origin.z=Z+3.2
            hit=ray(origin,-n,6)
            if PORTICO_GLASS:
                assert hit and hit[3] in ('glass','white') and 5.44-tolerance < hit[0] < 5.6+tolerance,('portico-open-bay',i,hit)
            else:
                assert hit and hit[3]=='white' and abs(hit[0]-5.6)<tolerance*2,('portico-open-bay',i,hit)
            foot=p-n;foot.z=Z+3.2
            floor=ray(foot,(0,0,-1),4)
            assert floor and floor[3]=='stone' and abs(floor[1].z-Z-.24)<tolerance,('portico-floor',i,floor)
            samples.append(dict(kind='portico-open-bay',bay=i,rearWallDistance=hit[0],floorHeight=floor[1].z-Z))
        if ENTRY_BAY:
            # Fixed mapped-entry projection, independent of the production
            # columns. This only checks the approach to the backing wall;
            # a doorway, stairs and road connection are not inferred.
            front=Vector((-695.20838278471,-742.4153550071646,0))
            for offset in (-.6,0,.6):
                for height in (1.,3.2,6.5):
                    origin=front+u*offset+n*2;origin.z=Z+height
                    hit=ray(origin,-n,6)
                    assert hit and 5.44-tolerance < hit[0] < 5.6+tolerance,('mapped-entry-approach',offset,height,hit)
                    samples.append(dict(kind='mapped-entry-approach',offset=offset,height=height,rearWallDistance=hit[0]))
    if PORTICO_GLASS:
        # Fixed adopted backing-wall endpoints; rays start behind the columns
        # so every glass cell is tested, without treating any cell as a door.
        a=Vector((-698.6939074704767,-760.4773988305454,0))
        b=Vector((-698.8909494339341,-729.4075449670695,0))
        length=(b-a).length;u=(b-a).normalized();n=Vector((u.y,-u.x,0))
        for col in range(12):
            p=a+u*(.03*length+.12+(col+.37)*(.94*length-.24)/12)
            for row in range(3):
                height=.6+.12+(row+.37)*(5.7-.24)/3
                origin=p+n*2;origin.z=Z+height
                hit=ray(origin,-n,3)
                assert hit and hit[3]=='glass' and hit[2].dot(n)>.98,('portico-glass-cell',col,row,hit)
                assert abs(hit[0]-1.96)<tolerance*2,('portico-glass-wall-depth',hit)
                samples.append(dict(kind='portico-glass-cell',column=col,row=row,distance=hit[0]))
        for fraction,height in [(.01,3.),(.99,3.),(.5,.4),(.5,6.5)]:
            origin=a.lerp(b,fraction)+n*2;origin.z=Z+height
            hit=ray(origin,-n,3)
            assert hit and hit[3]=='white' and abs(hit[0]-2)<tolerance*2,('portico-glass-boundary',fraction,height,hit)
            samples.append(dict(kind='portico-glass-boundary',fraction=fraction,height=height))
    if FOYER_PROFILE:
        # Samples span the four adopted slope intervals, plus fixed exposed
        # closure walls. Expectations are independent of prepared roof meshes.
        projected_area=0.
        for obj in objects:
            if obj.type!='MESH':continue
            obj.data.calc_loop_triangles()
            for tri in obj.data.loop_triangles:
                if obj.data.materials[tri.material_index].name.split('.')[0]!='paleRoof':continue
                a,b,c=[obj.matrix_world@obj.data.vertices[k].co for k in tri.vertices]
                if all(10.8-tolerance<=p.z-Z<=13.2+tolerance and -721<p.x<-698 and -761<p.y<-728 for p in (a,b,c)):
                    signed=(b-a).cross(c-a).z/2
                    assert signed>0,('profile-top-normal',signed)
                    projected_area+=signed
        assert abs(projected_area-631.617979)<tolerance*150,('profile duplicated roof or gap',projected_area)
        samples.append(dict(kind='single-covered-profile-top',projectedAreaMeters2=projected_area))
        for y in (-737.,-744.,-752.):
            for x in (-700.,-706.,-711.,-716.):
                roof(x,y,profile_height(x,y),'paleRoof','foyer-profile')
        for a,b in [((-720.2684733304854,-735.6025599999941),(-717.4120227129979,-760.4504602492385)),
                    ((-717.4120227129979,-760.4504602492385),(-698.6939074704767,-760.4773988305454))]:
            a,b=Vector((*a,0)),Vector((*b,0));p=a.lerp(b,.2)
            u=(b-a).normalized();n=Vector((u.y,-u.x,0))
            origin=p+n*1;origin.z=Z+11.5
            hit=ray(origin,-n,2)
            assert hit and hit[3]=='white' and hit[2].dot(n)>.98,('profile-rim-closure',p,hit)
            assert abs(hit[0]-1)<tolerance*2,('profile-rim-depth',hit)
            samples.append(dict(kind='profile-rim-closure',position=list(p),height=11.5))
    if ROOF_RIM:
        # Independent perimeter anchors and offsets check cap height, width,
        # exposed normals, and removal of the portico's old 0.8 m parapet.
        cap_edges = [
            ((-698.6939074704767,-760.4773988305454),(-698.8909494339341,-729.4075449670695),True),
            ((-720.2684733304854,-729.3909039997784),(-720.2684733304854,-735.6025599999941),True),
            ((-720.2684733304854,-735.6025599999941),(-717.4120227129979,-760.4504602492385),True),
            ((-717.4120227129979,-760.4504602492385),(-698.6939074704767,-760.4773988305454),True),
            ((-695.093802217242,-760.4825800000607),(-695.2908592664412,-729.4103473955927),False)]
        for a,b,profiled in cap_edges:
            a,b=Vector((*a,0)),Vector((*b,0));u=(b-a).normalized();n=Vector((u.y,-u.x,0))
            for t in (.25,.5,.75):
                p=a.lerp(b,t)
                for setback,cap in [(.17,True),(.55,False)]:
                    q=p-n*setback;h=profile_height(q.x,q.y) if profiled else 7.2
                    if cap:h+=.45 if profiled else .18
                    roof(q.x,q.y,h,'white' if cap else 'paleRoof','profile-rim' if profiled else 'portico-rim')
                q=p+n*.5;h=profile_height(p.x,p.y)+.2 if profiled else 7.29
                hit=ray((q.x,q.y,Z+h),-n,1)
                assert hit and hit[3]=='white' and hit[2].dot(n)>.98,('rim-outer-face',p,hit)
                assert abs(hit[0]-.5)<tolerance*2,('rim-outer-position',p,hit)
                samples.append(dict(kind='rim-outer-face',position=list(p),height=h))
        roof(-709.,-729.58,profile_height(-709.,-729.58),'paleRoof','foyer-profile')
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
report['labFacadeChecked']=LAB_FACADE
report['repartitionChecked']=REPARTITION
report['porticoGlazingChecked']=PORTICO_GLASS
report['foyerProfileChecked']=FOYER_PROFILE
report['roofRimChecked']=ROOF_RIM
report['entryBayChecked']=ENTRY_BAY
if REPARTITION:
    report['scope']='Estimated six-part correction: 6 m deep north low wing at 7.2 m, recessed 13.2 m hall, 10.8 m connector and six-column 7.2 m open portico. Office and west part retained. Relative layout checked against imagery; dimensions and entries remain unverified.'
if NORTH_FACADE:
    report['scope']+=' Includes estimated 22-column north grid, continuous white piers and upper solid east end; ground entry, other elevations and roof structures remain pending.'
if ROOF_VOLUMES:
    report['scope']+=' Includes two 1.1 m raised roof strips, west connection and 2.6 m southeast block, with open roof gaps. Roof dimensions and use remain estimates.'
if EAST_SLIT:
    report['scope']+=' Includes the photo-constrained narrow east glazing strip with eight estimated divisions and surrounding solid wall. Ground openings, corner return and use remain unverified.'
if LAB_FACADE:
    report['scope']+=' Includes the low-lab east 18-column three-row window grid and continuous white piers. Counts, dimensions and ground-row continuation are estimates; entry positions remain pending.'
if FOYER_PROFILE:
    report['scope']+=' Includes the four-segment west-rising foyer roof, with 2.4 m estimated rise and closed elevated boundaries.'
if ROOF_RIM:
    report['scope']+=' Includes a 0.35 m inset rim: 0.45 m high around exposed foyer edges and 0.18 m high along the portico exterior. Exact sections and drainage remain unverified.'
if ENTRY_BAY:
    report['scope']+=' Includes six estimated columns with one double-width bay supporting the mapped east-entry approach; actual column grid, doorway, stairs and road connection remain unverified.'
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
