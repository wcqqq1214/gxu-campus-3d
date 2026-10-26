"""Road retriangulation must retain material boundaries, holes and source data."""
import sys,unittest
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import Mesh,material
from terrain_planar import planar_terrain_candidate
class RoadPlanarTests(unittest.TestCase):
 def test_shared_domain_and_materials(self):
  m=Mesh();a=material('test-road',(.2,.2,.2));b=material('test-mark',(.8,.8,.5))
  for x in range(12):
   for y in range(8):
    if 4<=x<6 and 3<=y<5:continue
    m.face([(x,y,0),(x+1,y,0),(x+1,y+1,0),(x,y+1,0)],a if x<8 else b)
  o=m.object('road-planar-test',bpy.context.scene.collection,{'layer':'roads'});original=o.data
  with self.assertRaises(ValueError):
   with planar_terrain_candidate(o):pass
  with planar_terrain_candidate(o,shared_position_bounds=True) as report:
   self.assertGreater(report['removedFaces'],0)
   o.data.calc_loop_triangles();ts=list(o.data.loop_triangles)
   tree=BVHTree.FromPolygons([v.co for v in o.data.vertices],[tuple(t.vertices) for t in ts],all_triangles=True)
   for x in range(12):
    for y in range(8):
     hit,normal,index,_=tree.ray_cast(Vector((x+.4,y+.3,1)),Vector((0,0,-1)))
     if 4<=x<6 and 3<=y<5:self.assertIsNone(hit);continue
     self.assertIsNotNone(hit);self.assertAlmostEqual(hit.z,0,places=6)
     name=o.data.materials[ts[index].material_index].name
     self.assertEqual(name,'test-road' if x<8 else 'test-mark')
  self.assertIs(o.data,original)
if __name__=='__main__':
 if not unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RoadPlanarTests)).wasSuccessful():raise SystemExit(1)
