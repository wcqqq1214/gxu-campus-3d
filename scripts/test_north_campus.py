"""Delivered northern layout: provenance, topology, clear ground, and assets."""
import hashlib
import json
import math
import unittest
from pathlib import Path
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union
from surroundings_data import surface_shape

ROOT=Path(__file__).resolve().parents[1]


class NorthCampusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.read=staticmethod(lambda path:json.loads((ROOT/path).read_text()))
        cls.layout=cls.read('public/data/north-campus.json')
        cls.buildings=[b for b in cls.read('public/data/buildings.json') if b['id'].startswith('north-campus/')]

    def test_trace_is_separate_from_osm_and_has_capture_date(self):
        raw=self.read('data/north-campus-layout.json')
        self.assertEqual(raw['image']['capturedAt'],'2024-11-30')
        self.assertEqual({b['id'] for b in raw['buildings']},{b['id'] for b in self.buildings})
        for b in self.buildings:
            self.assertEqual(b['geometrySource'],'manual-imagery-trace')
            self.assertIsNone(b['osmEditedAt'])
            self.assertNotIn('openstreetmap.org',b['sourceUrl'])
            self.assertIn('估算',b['heightBasis'])

    def test_blocks_are_disjoint_and_outside_the_public_arterial(self):
        shapes=[Polygon(p[0],p[1:]) for b in self.buildings for p in b['polygons']]
        boundary=Polygon(self.layout['boundary']);road=Polygon(self.layout['publicRoad'])
        for i,p in enumerate(shapes):
            self.assertTrue(p.is_valid)
            self.assertTrue(boundary.buffer(.001).covers(p))
            self.assertTrue(p.exterior.is_ccw,'Exterior walls must face outward')
            self.assertLess(p.intersection(road).area,.01)
            for q in shapes[i+1:]:self.assertLess(p.intersection(q).area,.02)
        # Keep the three internal courtyard spaces, rather than filling the group.
        union=unary_union(shapes)
        self.assertGreater(union.convex_hull.area-union.area,3000)

    def test_ground_and_tree_crowns_do_not_occupy_new_buildings(self):
        solids=unary_union([Polygon(p[0],p[1:]) for b in self.buildings for p in b['polygons']])
        grounds=[surface_shape(g) for g in self.layout['grounds']]
        for g in grounds:self.assertLess(g.intersection(solids).area,.02)
        entries=[Polygon(b['northForm']['entryFootprint']) for b in self.buildings if b['northForm'].get('entryFootprint')]
        mask=unary_union([solids,*grounds,*entries])
        for tree in self.read('public/data/vegetation.json'):
            self.assertGreater(mask.distance(Point(tree[:2])),4*tree[2]/9+1)

    def test_model_manifest_tracks_both_lods(self):
        manifest=self.read('public/data/models.json')
        keys={b['chunk'] for b in self.buildings}
        for key in keys:
            zone=next(z for z in manifest['zones'] if z['id']==key)
            payload=(ROOT/'public'/zone['url']).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(),zone['sha256'])
            self.assertTrue({b['id'] for b in self.buildings if b['chunk']==key}<=set(zone['featureIds']))
        self.assertLessEqual(manifest['base']['bytes']+manifest['trees']['bytes'],6_000_000)

    def test_underpass_and_no_new_paving_over_existing_roads(self):
        passage=self.layout['underpass']
        self.assertEqual(passage['osmId'],'way/839763085')
        self.assertEqual(len(passage['upperRoadIds']),4)
        self.assertAlmostEqual(passage['soffit']-passage['floorElevation'],3.2)
        roads=unary_union([surface_shape(s) for s in self.read('public/data/surfaces.json') if s['kind']=='roads'])
        for ground in self.layout['grounds']:
            self.assertLess(surface_shape(ground).intersection(roads).area,.001)
        upper=unary_union([surface_shape(s) for s in self.read('public/data/surfaces.json') if s['id'] in passage['upperRoadIds']])
        cuts=unary_union([Polygon(p) for p in passage['roadMasks']])
        repairs=unary_union([Polygon(p['outline']) for p in passage['upperRoadRepairs']])
        self.assertLess(cuts.intersection(upper).difference(repairs.buffer(.001)).area,.001)
        self.assertEqual({p['roadId'] for p in passage['upperRoadRepairs']},set(passage['upperRoadIds']))

    def test_all_north_buildings_clear_original_roads(self):
        roads=unary_union([surface_shape(s) for s in self.read('public/data/surfaces.json') if s['kind']=='roads'])
        for b in self.buildings:
            shape=unary_union([Polygon(p[0],p[1:]) for p in b['polygons']])
            self.assertLess(shape.intersection(roads.buffer(1.2)).area,.001,b['id'])

    def test_boundary_overlay_does_not_cross_bridge_deck(self):
        edges=unary_union([LineString([p[:2] for p in ring]) for ring in self.read('public/data/campus-boundary.json')['rings']])
        for r in self.layout['underpass']['upperRoadRepairs']:
            self.assertLess(edges.intersection(Polygon(r['outline']).buffer(-.4)).length,.001)

    def test_photo_features_have_ground_level_passages(self):
        for b in self.buildings:
            form=b['northForm']
            if not form.get('portalWidth'):continue
            cx,cy=form['frame']['center'];ux,uy=form['frame']['u']
            u0,v0,u1,v1=form['frame']['bounds']
            for v in (v0+.4,(v0+v1)/2,v1-.4):
                point=Point(cx-v*uy,cy+v*ux)
                for part in form['solids']:
                    if part['bottom']<3.0:
                        self.assertFalse(any(Polygon(p[0],p[1:]).contains(point) for p in part['polygons']),b['id'])

    def test_documented_storeys_and_estimated_heights_are_separate(self):
        lab=next(b for b in self.buildings if b['id']=='north-campus/teaching-nw')
        self.assertEqual(lab['levels'],5)
        self.assertIn('2022',lab['levelsBasis'])
        self.assertIn('估算',lab['heightBasis'])
        gym=next(b for b in self.buildings if b['id']=='north-campus/gym')
        self.assertGreater(gym['height']-gym['northForm']['bodyHeight'],5)
        library=next(b for b in self.buildings if b['id']=='north-campus/library')
        self.assertGreater(library['height'],library['northForm']['bodyHeight'])
        self.assertGreater(Polygon(library['northForm']['entryFootprint']).area,300)


if __name__=='__main__':unittest.main()
