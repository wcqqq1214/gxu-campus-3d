import unittest
from collections import Counter
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from road_surface_clearance import load_repairs, repair_clearance, plane


class Mesh:
    def __init__(self):
        self.v=[]; self.f=[]; self.m=[]; self.parts=[]
        self.ground_uv_bounds=[]; self.xy_uv_materials=set()

    def face(self, points, material):
        start=len(self.v); self.v.extend(points)
        self.f.append(tuple(range(start,len(self.v)))); self.m.append(material)


class RoadSurfaceClearanceTests(unittest.TestCase):
    def test_terrain_peak_is_covered_without_overlays_or_uv_changes(self):
        road, terrain = Mesh(), Mesh()
        road.face([(-2,-2,0),(2,-2,0),(2,2,0)],0)
        road.face([(-2,-2,0),(2,2,0),(-2,2,0)],0)
        road.face([(8,8,1),(9,8,1),(8,9,1)],1)
        road.source_uvs=[[(road.v[i][0]/4,road.v[i][1]/4) for i in f] for f in road.f]
        corners=[(-2,-2,-.5),(2,-2,-.5),(2,2,-.5),(-2,2,-.5)]
        for a,b in zip(corners,corners[1:]+corners[:1]):
            terrain.face([a,b,(0,0,.5)],0)
        repairs=[{'bounds':[-2,-2,2,2],'clearance':.08,'maxLift':.8}]
        fixed,report=repair_clearance(road,terrain,0,repairs)
        self.assertEqual(report['changedFaces'],2)
        self.assertAlmostEqual(report['maxLift'],.58)
        polygons=[Polygon([fixed.v[i][:2] for i in f]) for f,m in zip(fixed.f,fixed.m) if m==0]
        self.assertAlmostEqual(sum(p.area for p in polygons),16)
        self.assertAlmostEqual(unary_union(polygons).area,16)
        # Every interior edge is shared exactly, so quantizing both faces
        # cannot open a T-junction crack along the split terrain contour.
        edges = Counter()
        for f,m in zip(fixed.f,fixed.m):
            if m != 0:
                continue
            ps = [tuple(round(v,7) for v in fixed.v[i]) for i in f]
            for a,b in zip(ps,ps[1:]+ps[:1]):
                edges[tuple(sorted((a,b)))] += 1
        for (a,b), count in edges.items():
            boundary = any(a[k] == b[k] and abs(a[k]) == 2 for k in (0,1))
            self.assertEqual(count, 1 if boundary else 2, (a,b))
        for f,uvs in zip(fixed.f,fixed.source_uvs):
            for i,uv in zip(f,uvs):
                self.assertAlmostEqual(uv[0],fixed.v[i][0]/4)
                self.assertAlmostEqual(uv[1],fixed.v[i][1]/4)
        for x in [-1.75,-1.25,-.75,-.25,.25,.75,1.25,1.75]:
            for y in [-1.75,-1.25,-.75,-.25,.25,.75,1.25,1.75]:
                # Independent pyramid equation, not the clipping implementation.
                expected=max(0,.5-.5*max(abs(x),abs(y))+.08)
                values=[]
                for f,m in zip(fixed.f,fixed.m):
                    ps=[fixed.v[i] for i in f]
                    if m==0 and Polygon([p[:2] for p in ps]).covers(Point(x,y)):
                        a,b,c=plane(*ps[:3]);values.append(a*x+b*y+c)
                self.assertTrue(values)
                for value in values:self.assertAlmostEqual(value,expected)
        self.assertIn(road.f[-1],fixed.f)
        twice,second=repair_clearance(fixed,terrain,0,repairs)
        self.assertEqual(second['changedFaces'],0)
        self.assertEqual(twice.f,fixed.f)

    def test_large_unexpected_displacement_is_rejected(self):
        road,terrain=Mesh(),Mesh()
        road.face([(0,0,0),(2,0,0),(0,2,0)],0)
        terrain.face([(0,0,10),(2,0,10),(0,2,10)],0)
        with self.assertRaises(ValueError):
            repair_clearance(road,terrain,0,[{'bounds':[0,0,2,2],'clearance':.08,'maxLift':.8}])

    def test_material_scopes_do_not_raise_neighboring_surface_or_duplicate_faces(self):
        road, terrain = Mesh(), Mesh()
        for mat in (0, 1, 2):
            road.face([(0,0,0),(4,0,0),(4,4,0),(0,4,0)], mat)
        terrain.face([(0,0,.2),(4,0,.2),(4,4,.2),(0,4,.2)], 0)
        repairs = [dict(material=mat, bounds=[0,0,2,4], clearance=.08, maxLift=.4)
                   for mat in ('road', 'path')]
        fixed, report = repair_clearance(road, terrain, {'asphalt':0,'road':1,'path':2}, repairs)
        self.assertEqual(report['changedFaces'], 2)
        self.assertAlmostEqual(report['raisedArea'], 16)
        self.assertEqual(fixed.changed_materials, {1, 2})
        self.assertEqual(fixed.f[0], road.f[0])
        for mat in (1, 2):
            polygons = [Polygon([fixed.v[i][:2] for i in f])
                        for f, m in zip(fixed.f, fixed.m) if m == mat]
            self.assertAlmostEqual(sum(p.area for p in polygons), 16)
            self.assertAlmostEqual(unary_union(polygons).area, 16)
            for x, expected in [(1, .28), (3, 0)]:
                heights = []
                for f, m in zip(fixed.f, fixed.m):
                    points = [fixed.v[i] for i in f]
                    if m == mat and Polygon([p[:2] for p in points]).covers(Point(x, 1.5)):
                        a, b, c = plane(*points[:3])
                        heights.append(a*x+b*1.5+c)
                self.assertTrue(heights)
                for h in heights:
                    self.assertAlmostEqual(h, expected)
        _, second = repair_clearance(fixed, terrain, {'road':1,'path':2}, repairs)
        self.assertEqual(second['changedFaces'], 0)

    def test_loader_rejects_duplicate_coverage_and_unknown_ids(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'data').mkdir()
            path = root/'data/road-surface-clearance.json'
            a = dict(id='a', material='road', bounds=[0,0,4,4], clearance=.08, maxLift=.4)
            b = dict(a, id='b', bounds=[2,2,6,6])
            path.write_text(json.dumps({'repairs':[a,b]}))
            with self.assertRaisesRegex(ValueError, 'Overlapping'):
                load_repairs(root)
            b['material'] = 'path'
            path.write_text(json.dumps({'repairs':[a,b]}))
            self.assertEqual(load_repairs(root, ['b']), [b])
            with self.assertRaisesRegex(ValueError, 'Unknown'):
                load_repairs(root, ['typo'])


if __name__=='__main__':unittest.main()
