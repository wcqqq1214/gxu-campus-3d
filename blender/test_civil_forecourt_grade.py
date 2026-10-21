"""Civil entrance must stay shallow on coarse, roof-contaminated DEM faces."""
import sys, unittest
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import Mesh
from civil_forecourt_grade import load_grade, grade_forecourt, height, building_datum, weight
class CivilGradeTests(unittest.TestCase):
 def test_coarse_dem_and_road_hole(self):
  p=load_grade(ROOT);g=Mesh();r=Mesh()
  g.face([(-520,-920,1),(-330,-920,12),(-330,-700,12),(-520,-700,1)],7)
  # Two road strips with a genuine gap must remain two strips.
  for y in (-846,-874):r.face([(-510,y,2),(-450,y,11),(-450,y+4,11),(-510,y+4,2)],9)
  gg,rr=grade_forecourt(g,r,p)
  gt,rt=(BVHTree.FromPolygons(m.v,m.f) for m in (gg,rr))
  def at(t,x,y):return t.ray_cast(Vector((x,y,50)),Vector((0,0,-1)))[0]
  for y in (-844,-872):
   hs=[]
   for i in range(95):
    x=-502+i*.5
    if y==-872 and x<-460:continue
    ground=at(gt,x,y);road=at(rt,x,y)
    self.assertAlmostEqual(ground.z,height(x,y,p),delta=.012)
    self.assertAlmostEqual(road.z-ground.z,.12,delta=.002);hs.append(road.z)
   self.assertLess(max(abs(b-a) for a,b in zip(hs,hs[1:])),.025)
  self.assertIsNone(at(rt,-485,-860))
  # Outside faces and the exact fade boundary keep their prior plane.
  original=BVHTree.FromPolygons(g.v,g.f)
  for x,y in [(-518,-890),(-340,-855),(-480,-900),(-480,-710),(-500,-877.55),(-490,-882)]:
   self.assertAlmostEqual(at(gt,x,y).z,at(original,x,y).z,delta=.002)
  self.assertEqual(set(rr.m),{9})
  # Grade-control seams stay below 1 cm, tighter than the 2.5 cm export budget.
  for i in range(117):
   y=-899+i*.5
   self.assertAlmostEqual(at(gt,-451-.0001,y).z,at(gt,-451+.0001,y).z,delta=.01,msg=f'east seam y={y}')
  for i in range(117):
   x=-509+i*.5
   self.assertAlmostEqual(at(gt,x,-840-.0001).z,at(gt,x,-840+.0001).z,delta=.01,msg=f'north seam x={x}')
 def test_pad_cut_does_not_leave_a_height_seam(self):
  # A pad cuts only one side of a grid edge. Nonlinear grading must not
  # leave its new vertex hanging above the adjacent unsplit triangle.
  p=load_grade(ROOT);p.update(meshStep=10,detailStep=4,detailBounds=[-510,-900,-451,-840]);g=Mesh()
  g.face([(-410,-830,4),(-370,-830,4),(-370,-800,4),(-410,-800,4)],7)
  from civil_forecourt_grade import grade_mesh
  graded=grade_mesh(g,p);tree=BVHTree.FromPolygons(graded.v,graded.f)
  def at(x,y):return tree.ray_cast(Vector((x,y,50)),Vector((0,0,-1)))[0].z
  for y in (-812,-811,-810.1):
   self.assertAlmostEqual(at(-389.44-.0001,y),at(-389.44+.0001,y),delta=.0003,msg=f'pad seam y={y}')
 def test_fade_reduces_excess_road_soil_gap(self):
  p=load_grade(ROOT);g=Mesh();r=Mesh()
  ring=[(-510,-860),(-500,-860),(-500,-840),(-510,-840)]
  g.face([(x,y,0) for x,y in ring],7);r.face([(x,y,1) for x,y in ring],9)
  gg,rr=grade_forecourt(g,r,p)
  gt,rt=(BVHTree.FromPolygons(m.v,m.f) for m in (gg,rr))
  def gap(x):
   q=Vector((x,-850,50));d=Vector((0,0,-1))
   return rt.ray_cast(q,d)[0].z-gt.ray_cast(q,d)[0].z
  self.assertAlmostEqual(gap(-510),1,delta=.002)
  self.assertLess(gap(-506),.3)
  self.assertGreater(gap(-506),.065)
  self.assertAlmostEqual(gap(-502),.12,delta=.002)
 def test_context_floor_and_outer_transition(self):
  p=load_grade(ROOT)
  for pad in p['contextPads']:
   a,b,c,d=pad['bounds'];x=(a+c)/2;y=(b+d)/2
   self.assertAlmostEqual(weight(x,y,p),1)
   self.assertAlmostEqual(height(x,y,p),pad['datum']-.02)
   self.assertEqual(building_datum({'id':pad['buildingId']},12,p),pad['datum'])
  self.assertEqual(building_datum({'id':'unrelated'},12,p),12)
  # The former four-metre east cliff is now part of a continuous low field.
  for y in (-850,-842,-812):
   z=[height(-455+i*.25,y,p) for i in range(20)]
   self.assertLess(max(z)-min(z),.15)
   self.assertTrue(all(weight(-455+i*.25,y,p)>.99 for i in range(20)))
  self.assertGreaterEqual(p['northTie']['end']-p['northTie']['start'],80)
if __name__=='__main__':
 if not unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CivilGradeTests)).wasSuccessful():raise SystemExit(1)
