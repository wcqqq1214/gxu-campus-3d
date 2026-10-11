import unittest
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from road_surface_clearance import repair_clearance, plane


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


if __name__=='__main__':unittest.main()
