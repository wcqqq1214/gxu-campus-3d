"""Grade an interior road patch; retain its footprint, boundary and outside planes."""
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from geometry import Mesh
from site_geometry import mesh_triangles, split_convex
from shore_geometry import bounds, overlaps, triangles_into, conform_edges


def local(record, point):
    delta = [point[i] - record['origin'][i] for i in range(2)]
    return (sum(delta[i] * record['tangent'][i] for i in range(2)),
            sum(delta[i] * record['normal'][i] for i in range(2)))


def world(record, x, y):
    return tuple(record['origin'][i] + record['tangent'][i]*x + record['normal'][i]*y for i in range(2))


def ramp(value):
    return max(0, min(1, value))


def weight(record, point):
    x, y = local(record, point)
    start, flat_start, flat_end, end = record['depthStations']
    width, side = record['halfWidth'], record['sideFeather']
    return (ramp((width + side - abs(x))/side) *
            ramp((y-start)/(flat_start-start)) * ramp((end-y)/(end-flat_end)))


def area(points):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))) / 2


def stations(anchors, step):
    result = []
    for a, b in zip(anchors, anchors[1:]):
        count = math.ceil((b-a)/step)
        result.extend(a+(b-a)*i/count for i in range(count))
    return result + [anchors[-1]]


def build_landing(record, roads, terrain, road_material):
    width, side = record['halfWidth'], record['sideFeather']
    start, _, _, end = record['depthStations']
    outline = [world(record,x,y) for x,y in [(-width-side,start),(width+side,start),(width+side,end),(-width-side,end)]]
    region = bounds(outline)
    # Exact area coverage by the pinned map triangles rules out a patch outside
    # the named road (including concave boundaries), rather than just four corners.
    surface = record['surface']; coverage = 0
    for i in range(0,len(surface['triangles']),3):
        points = [(*surface['vertices'][k],0) for k in surface['triangles'][i:i+3]]
        kept, _ = split_convex(points,outline)
        coverage += area(kept) if kept else 0
    expected = 2*(width+side)*(end-start)
    if abs(coverage-expected) > .001:
        raise ValueError(('Landing leaves mapped road',coverage,expected))
    xs = stations([-width-side,-width,width,width+side],record['meshStep'])
    ys = stations(record['depthStations'],record['meshStep'])
    cells = [[world(record,x,y) for x,y in [(a,c),(b,c),(b,d),(a,d)]]
             for a,b in zip(xs,xs[1:]) for c,d in zip(ys,ys[1:])]
    selected = {i for i,f in enumerate(roads.f) if overlaps(bounds([roads.v[k] for k in f]),region)}
    result = Mesh(); actual_area = 0
    for i,face in enumerate(roads.f):
        if i not in selected:result.face([roads.v[k] for k in face],roads.m[i])
    for ids,face in mesh_triangles(roads):
        if face not in selected:continue
        original = [roads.v[k] for k in ids]
        kept, outside = split_convex(original,outline)
        if not kept or area(kept)<1e-9:
            result.face(original,roads.m[face]);continue
        if roads.m[face] != road_material:
            raise ValueError('Landing intersects a different road material')
        actual_area += area(kept)
        for part in outside:triangles_into(result,part,roads.m[face])
        for cell in cells:
            part,_ = split_convex(kept,cell)
            triangles_into(result,part,roads.m[face])
    if abs(actual_area-expected) > .002:
        raise ValueError(('Missing or overlapping actual road surface',actual_area,expected))
    # Conform BEFORE changing heights: shared cut edges must receive the same
    # grade, while all interpolated outside points stay on their original plane.
    affected = bounds([roads.v[k] for i in selected for k in roads.f[i]])
    result = conform_edges(result,[v+(-1 if i<2 else 1)*.01 for i,v in enumerate(affected)],preserve_vertical_faces=True)
    target = record['targetElevation']
    result.v = [(x,y,z+(target-z)*weight(record,(x,y))) for x,y,z in result.v]
    ground = BVHTree.FromPolygons(terrain.v,[t for t,_ in mesh_triangles(terrain)],all_triangles=True)
    minimum = math.inf
    # All modified triangle vertices and centroids: terrain is independently
    # checked again on a dense grid against the exported candidate.
    for face in result.f:
        points = [result.v[k] for k in face]
        if not any(weight(record,p)>1e-9 for p in points):continue
        for p in points+[tuple(sum(v[k] for v in points)/len(points) for k in range(3))]:
            hit = ground.ray_cast(Vector((p[0],p[1],target+20)),Vector((0,0,-1)),40)[0]
            if hit is None:raise ValueError('Missing terrain under landing')
            minimum = min(minimum,p[2]-hit.z)
    if minimum < record['minimumTerrainClearance']:
        raise ValueError(('Landing terrain intrusion',minimum))
    return result, dict(id=record['id'],mappedInteriorArea=expected,targetElevation=target,
                        minimumSampledTerrainClearance=minimum,originalRoadFaces=len(roads.f),
                        finalRoadFaces=len(result.f),bounds=region,terrainUnchanged=True)


def build_landings(records, roads, terrain, road_material):
    reports=[]
    for record in records:
        roads,report=build_landing(record,roads,terrain,road_material);reports.append(report)
    return roads,reports
