"""Both LODs must preserve the tall narrow shaft and wider tank, not a house."""
import json,sys,unittest
from pathlib import Path
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import MATERIALS,material
from generic_buildings import ordinary_building
from student_water_tower import TOWER_ID

class TowerGeometry(unittest.TestCase):
    def test_tank_overhang_and_height_in_both_lods(self):
        b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']==TOWER_ID)
        c={name:material(name,(.5,.5,.5)) for name in ('dark','stone','metal','white')}
        x,y=b['center'];h=b['height']
        config=json.loads((ROOT/'data/building-overrides.json').read_text())['buildings'][TOWER_ID]
        self.assertEqual(config['evidence']['height']['status'],'estimated')
        self.assertEqual(b['height'],config['height'])
        for detail in (False,True):
            with self.subTest(detail=detail):
                m=ordinary_building(b,0,c,detail);tree=BVHTree.FromPolygons(m.v,m.f)
                # Two metres from centre: outside shaft, inside the tank.
                self.assertIsNone(tree.ray_cast((x+2.3,y,10),(0,0,1),8)[0])
                hit=tree.ray_cast((x+2.3,y,h+1),(0,0,-1),5)[0]
                self.assertIsNotNone(hit);self.assertAlmostEqual(hit.z,h,places=3)
                self.assertTrue(tree.ray_cast((x,y+5,10),(0,-1,0),6)[0] is not None)
                self.assertTrue(all(0<=v[2]<=h+2.66 for v in m.v))
                names={MATERIALS[i].name for i in m.m}
                self.assertIn('studentTowerBrick',names);self.assertIn('studentTowerTank',names)

result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TowerGeometry))
if not result.wasSuccessful():raise SystemExit(1)
