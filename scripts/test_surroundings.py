"""Validate delivered polygons independently of the road preparation algorithm."""
import json,sys,unittest,math
from pathlib import Path
from shapely.geometry import Polygon,LineString,shape
from shapely.ops import unary_union,transform
sys.path.insert(0,str(Path(__file__).resolve().parent))
from prepare_geodata import project
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'public/data'
def read(name):return json.loads((D/name).read_text())
def geometry(layer):
    v,t=layer['vertices'],layer['triangles']
    return unary_union([Polygon([v[j] for j in t[i:i+3]]) for i in range(0,len(t),3)])
class SurroundingsTest(unittest.TestCase):
    def test_road_surfaces_are_disjoint_and_outside_buildings(self):
        data=read('surroundings.json');geo=read('geography.geojson');campus=transform(project,shape(next(f for f in geo['features'] if f['id']=='campus')['geometry']))
        shapes=[geometry(s) for s in data['layers']]
        obstacles=unary_union([Polygon(p[0],p[1:]) for b in read('buildings.json') for p in b['polygons']])
        for i,g in enumerate(shapes):
            self.assertTrue(g.is_valid);self.assertLess(g.intersection(campus).area,1e-5)
            self.assertLess(g.intersection(obstacles).area,1e-5)
            for other in shapes[:i]:self.assertLess(g.intersection(other).area,1e-5)
        infra=read('infrastructure.json');surfaces=read('surfaces.json')
        for key in data['surfaceOverrides']:
            self.assertNotIn(surfaces[int(key)]['id'],infra['replaceSurfaceIds'])
        self.assertTrue(any(s['name']=='大学东路' for s in data['sources']))
    def test_boundary_matches_campus_with_public_corridor_removed(self):
        data=read('campus-boundary.json');geo=read('geography.geojson');expected=transform(project,shape(next(f for f in geo['features'] if f['id']=='campus-display-area')['geometry']))
        actual=[]
        for ring in data['rings']:
            self.assertEqual(ring[0],ring[-1]);self.assertTrue(all(len(p)==3 and all(math.isfinite(v) for v in p) for p in ring))
            self.assertLess(max(math.dist(a[:2],b[:2]) for a,b in zip(ring,ring[1:])),10.1)
            actual.append(LineString([p[:2] for p in ring]))
        self.assertLess(unary_union(actual).hausdorff_distance(expected.boundary),.36)
        self.assertGreater(len(actual),1)
if __name__=='__main__':unittest.main()
