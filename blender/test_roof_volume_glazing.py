"""Blender regression: all named faces face out for either anchor winding."""
import math
from pathlib import Path
import sys
import unittest
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0,str(Path(__file__).resolve().parent))
from geometry import Mesh
from roof_volume_glazing import add_roof_volume_glazing


class RoofWindowGeometryTests(unittest.TestCase):
    def test_all_faces_under_rotations_and_windings(self):
        for angle in (0,.73,2.8):
            for winding in (-1,1):
                with self.subTest(angle=angle,winding=winding):
                    u = Vector((math.cos(angle),math.sin(angle),0))
                    n = Vector((-u.y*winding,u.x*winding,0))
                    g = dict(faces={'outer':4,'inner':4,'start':2,'end':2},sill=3.6,
                             height=2,margin=.35,frameWidth=.25,projection=.12)
                    v = dict(angle=angle,center=[17,-4],outwardNormal=list(n)[:2],
                             width=12,depth=7,baseHeight=23.1,rise=6,glazing=g)
                    mesh=Mesh();add_roof_volume_glazing(mesh,v,1.99,{'white':0,'glass':1})
                    tree=BVHTree.FromPolygons(mesh.v,mesh.f)
                    self.assertTrue(all(math.isfinite(x) for p in mesh.v for x in p))
                    for f in mesh.f:
                        a,b,c=[Vector(mesh.v[i]) for i in f[:3]]
                        self.assertGreater((b-a).cross(c-a).length,1e-8)
                    for face, normal, offset, span in (
                            ('outer',n,3.5,12),('inner',-n,3.5,12),
                            ('start',-u,6,7),('end',u,6,7)):
                        tangent=Vector((-normal.y,normal.x,0))
                        span-=2*g['margin']; fw=g['frameWidth']
                        along=-(span-fw)/2+(span-fw)/g['faces'][face]/2
                        center=Vector((17,-4,29.69))+normal*offset+tangent*along
                        hit=tree.ray_cast(center+normal*.6,-normal,1)
                        self.assertIsNotNone(hit[0])
                        self.assertEqual(mesh.m[hit[2]],1)
                        self.assertGreater(hit[1].dot(normal),.99)
                        self.assertAlmostEqual((hit[0]-center).dot(normal),.015,places=4)
                        column=center-tangent*along+tangent*(-(span-fw)/2)
                        hit=tree.ray_cast(column+normal*.6,-normal,1)
                        self.assertIsNotNone(hit[0])
                        self.assertEqual(mesh.m[hit[2]],0)
                        self.assertAlmostEqual((hit[0]-column).dot(normal),.12,places=4)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RoofWindowGeometryTests))
    if not result.wasSuccessful():raise RuntimeError('Roof glazing geometry regression')
