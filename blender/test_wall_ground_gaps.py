"""Actual BVH fixtures for walls at, above, and below the adopted datum."""
import copy
import sys
import unittest
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, str(Path(__file__).resolve().parent))
from inspect_wall_ground_gaps import probes, check


def horizontal(z):
    return BVHTree.FromPolygons([Vector((x,y,z)) for x,y in [(-10,-10),(10,-10),(10,10),(-10,10)]], [(0,1,2,3)])


def wall(bottom):
    return BVHTree.FromPolygons([Vector(p) for p in [(0,0,bottom),(4,0,bottom),(4,0,4),(0,0,4)]], [(0,1,2,3)])


def building():
    return {'elevation':0, 'form':{'parts':[], 'facades':[
        {'part':'body','start':[0,0],'end':[4,0],'normal':[0,-1]}]}}


class WallContactTests(unittest.TestCase):
    def test_level_ground_requires_nonempty_contact_rays(self):
        rows=probes(building(),horizontal(0),horizontal(-20))
        self.assertEqual(len(rows),2)
        self.assertTrue(check(wall(-.5),rows)['passed'])
        self.assertEqual(check(wall(-.5),rows)['rays'],2)
        # A 20 cm gap above the floor must fail even though no ground lies below datum.
        self.assertEqual(check(wall(.2),rows)['openGapLocations'],2)

    def test_ground_slightly_above_datum_still_checks_wall(self):
        rows=probes(building(),horizontal(.1),horizontal(-20))
        self.assertTrue(check(wall(-.5),rows)['passed'])
        self.assertFalse(check(wall(.3),rows)['passed'])

    def test_higher_road_is_the_contact_surface(self):
        rows=probes(building(),horizontal(-1),horizontal(.2))
        # A wall beginning at zero meets the road, despite the lower terrain.
        self.assertTrue(check(wall(0),rows)['passed'])
        self.assertFalse(check(wall(.4),rows)['passed'])

    def test_below_datum_gap_remains_detected(self):
        rows=probes(building(),horizontal(-1),horizontal(-20))
        self.assertGreater(check(wall(-1.1),rows)['rays'],2)
        self.assertTrue(check(wall(-1.1),rows)['passed'])
        self.assertFalse(check(wall(-.5),rows)['passed'])

    def test_open_portico_and_upper_facade_are_excluded(self):
        b=building();b['form']['parts']=[{'id':'portico','openBelow':{'clearHeight':3}}]
        for part,minimum in [('portico',0),('upper',2)]:
            f=copy.deepcopy(b['form']['facades'][0]);f.update(part=part,minimumHeight=minimum)
            b['form']['facades'].append(f)
        self.assertEqual(len(probes(b,horizontal(0),horizontal(-20))),2)
        b['form']['facades']=b['form']['facades'][1:]
        with self.assertRaises(ValueError):probes(b,horizontal(0),horizontal(-20))

    def test_open_ground_gallery_checks_floor_and_rear_wall(self):
        b=building();b['form']['facades'][0]['rule']={'openCorridor':{
            'firstLevel':0,'endInset':.3,'depth':1.8}}
        def gallery(floor=True,rear=True,floor_z=0):
            vertices=[];faces=[]
            for enabled,points in [(floor,[(0,0,floor_z),(4,0,floor_z),(4,1.8,floor_z),(0,1.8,floor_z)]),
                                   (rear,[(0,1.8,0),(4,1.8,0),(4,1.8,4),(0,1.8,4)])]:
                if enabled:
                    start=len(vertices);vertices.extend(Vector(p) for p in points);faces.append(tuple(range(start,start+4)))
            return BVHTree.FromPolygons(vertices,faces)
        rows=probes(b,horizontal(0),horizontal(-20))
        result=check(gallery(),rows)
        self.assertTrue(result['passed']);self.assertEqual(result['openCorridorContactLocations'],2)
        for mesh in [gallery(floor=False),gallery(rear=False),gallery(floor_z=.2)]:
            self.assertFalse(check(mesh,rows)['passed'])
        for ground,road in [(horizontal(.2),horizontal(-20)),(horizontal(0),horizontal(.2))]:
            self.assertFalse(check(gallery(),probes(b,ground,road))['passed'])
        self.assertFalse(check(gallery(),probes(b,horizontal(-1),horizontal(-20)))['passed'])
        b['form']['facades'][0]['rule']['openCorridor']['endInset']=1.5
        self.assertFalse(check(gallery(),probes(b,horizontal(0),horizontal(-20)))['passed'])
        b['form']['facades'][0]['rule']['openCorridor']['endInset']=.3
        b['form']['facades'][0]['rule']['openCorridor']['firstLevel']=1
        self.assertFalse(check(gallery(),probes(b,horizontal(0),horizontal(-20)))['passed'])

    def test_missing_ground_is_not_a_pass(self):
        b=building();b['form']['facades'][0].update(start=[20,0],end=[24,0])
        with self.assertRaises(ValueError):probes(b,horizontal(0),horizontal(-20))


suite=unittest.defaultTestLoader.loadTestsFromTestCase(WallContactTests)
result=unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():raise AssertionError('Wall contact fixtures failed')
