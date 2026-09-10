"""Check delivered court placement and earthworks against independent map geometry."""
import json,math,unittest
from pathlib import Path
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
from surroundings_data import surface_shape
D=Path(__file__).resolve().parents[1]/'public/data'
def read(n):return json.loads((D/n).read_text())
class BasketballTest(unittest.TestCase):
    def test_mapped_centers_and_existing_selection(self):
        d=read('basketball.json');self.assertEqual(len(d['courts']),31)
        self.assertEqual(sum(c['insideCampus'] for c in d['courts']),16)
        for c in d['courts']:
            self.assertLess(Polygon(c['mappedFootprint']).centroid.distance(Point(c['center'])),.02)
            self.assertAlmostEqual(Polygon(c['footprint']).area,420,places=5)
            self.assertEqual(c['rimHeight'],3.05)
        self.assertEqual(len(read('landmarks.json')),19)
        self.assertEqual(len(d['areas']),2)
    def test_playing_areas_and_paving_do_not_intersect_obstacles(self):
        d=read('basketball.json');buildings=unary_union([Polygon(p[0],p[1:]) for b in read('buildings.json') for p in b['polygons']])
        obstacles=unary_union([buildings]+[surface_shape(s) for s in read('surfaces.json') if s['kind'] in ('roads','water')])
        for bank in d['banks']:
            g=Polygon(bank['ground']);self.assertLess(g.intersection(obstacles).area,1e-5)
            courts=[c for c in d['courts'] if c['bank']==bank['id']]
            for i,c in enumerate(courts):
                self.assertTrue(g.covers(Polygon(c['footprint'])))
                for other in courts[:i]:self.assertLess(Polygon(c['footprint']).intersection(Polygon(other['footprint'])).area,1e-5)
        self.assertFalse(set(d['terrainCells'])&set(read('infrastructure.json')['terrainCells']))
    def test_bank_terrain_contains_no_holes(self):
        d=read('basketball.json');patch=unary_union([Polygon([p['vertices'][i][:2] for i in p['triangles'][j:j+3]]) for p in d['terrainPatch'] for j in range(0,len(p['triangles']),3)])
        for bank in d['banks']:self.assertLess(Polygon(bank['ground']).difference(patch).area,1e-4)
        self.assertTrue(all(math.isfinite(v) for p in d['terrainPatch'] for xyz in p['vertices'] for v in xyz))
if __name__=='__main__':unittest.main()
