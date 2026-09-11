"""Geographical invariants for the six transition aprons."""
import json,unittest
from pathlib import Path
from shapely.geometry import Point
from surroundings_data import surface_shape
R=Path(__file__).resolve().parents[1]
D=json.loads((R/'public/data/campus-roads.json').read_text())
class Joins(unittest.TestCase):
    def test_six_mouths_partition(self):
        self.assertEqual(len(D['bridgeJoins']),6)
        for j in D['bridgeJoins']:
            layers=[surface_shape(l) for l in j['layers'] if not l.get('zOffset')]
            for i,g in enumerate(layers):
                for h in layers[i+1:]:self.assertLess(g.intersection(h).area,1e-5,j['id'])
            self.assertTrue(layers[0].buffer(.01).covers(Point(j['axis'][0])),j['id'])
            self.assertTrue(layers[0].buffer(.01).covers(Point(j['axis'][-1])),j['id'])
    def test_join_asphalt_clear_of_campus_kerbs(self):
        curb=surface_shape(next(l for l in D['layers'] if l['material']=='curb'))
        for j in D['bridgeJoins']:
            asphalt=surface_shape(next(l for l in j['layers'] if l['material']=='asphalt'))
            self.assertLess(asphalt.intersection(curb).area,1e-5,j['id'])
if __name__=='__main__':unittest.main()
