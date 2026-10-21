import copy,json,unittest,shutil,tempfile,contextlib,io
from pathlib import Path
from shapely.geometry import Polygon
from surroundings_data import surface_shape
from recessed_entry_site_data import derive_recessed_entry_site
from audit_entry_road_context import effective_road_surfaces

ROOT=Path(__file__).resolve().parents[1]


class RecessedEntryGroundTests(unittest.TestCase):
    def setUp(self):
        read=lambda path:json.loads((ROOT/path).read_text())
        self.buildings=read('public/data/buildings.json')
        self.config=next(v for v in read('data/site-overrides.json')['sites'] if v.get('type')=='recessed-entry-ground')
        self.sources={v['id'] for v in read('public/data/sources.json')['sources']}

    def test_forecourt_stops_before_perimeter_roads(self):
        site,area,_=derive_recessed_entry_site(self.config,self.buildings,self.sources)
        self.assertGreater(area.area,1100)
        self.assertLess(area.area,1200)
        raw=json.loads((ROOT/'public/data/surfaces.json').read_text())
        effective={v['id']:v for v in effective_road_surfaces()}
        from shore_data import effective_surfaces
        layers=[json.loads((ROOT/f'public/data/{name}.json').read_text()) for name in ('infrastructure','surroundings','campus-roads')]
        before_site={v['id']:v for v in effective_surfaces(raw,[v['surfaceOverrides'] for v in layers],set(layers[0]['replaceSurfaceIds']))}
        for ident in ('way/685682496','way/759096567','way/759096574'):
            original=next(v for v in raw if v['id']==ident)
            self.assertEqual(before_site[ident]['vertices'],effective[ident]['vertices'])
            self.assertEqual(before_site[ident]['triangles'],effective[ident]['triangles'])
            self.assertGreater(area.distance(surface_shape(original)),.02)
        service=next(v for v in raw if v['id']=='way/842784663')
        before=surface_shape(before_site[service['id']]);after=surface_shape(effective[service['id']])
        self.assertAlmostEqual(before.difference(area).symmetric_difference(after).area,0,places=6)
        self.assertGreater(after.area,0) # Uncovered road fragments are not discarded.
        rendered=json.loads((ROOT/'public/data/campus-roads.json').read_text())['layers']
        for layer in rendered:
            self.assertLess(area.intersection(surface_shape(layer)).area,1e-6)
        self.assertLess(area.distance(surface_shape(next(s for s in raw if s['id']=='way/759096567'))),.04)
        self.assertLess(area.distance(surface_shape(next(s for s in raw if s['id']=='way/759096574'))),.6)

    def test_stale_or_unsourced_layout_rejected(self):
        for key,value in [('footprintRevision','old'),('sourceRefs',['missing']),('entranceId','missing'),('groundClearance',True),('groundClearance',1)]:
            config=copy.deepcopy(self.config);config[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                derive_recessed_entry_site(config,self.buildings,self.sources)

    def test_overlap_with_neighbor_rejected(self):
        _,area,_=derive_recessed_entry_site(self.config,self.buildings,self.sources)
        neighbor={'id':'neighbor','polygons':[[list(area.exterior.coords)]]}
        with self.assertRaisesRegex(ValueError,'mapped building'):
            derive_recessed_entry_site(self.config,self.buildings+[neighbor],self.sources)

    def test_preparation_does_not_depend_on_model_build_elevation(self):
        fresh=copy.deepcopy(self.buildings)
        for b in fresh:
            for key in ('elevation','chunk','zone'):b.pop(key,None)
        site,_,_=derive_recessed_entry_site(self.config,fresh,self.sources)
        cached=copy.deepcopy(fresh)
        next(b for b in cached if b['id']==self.config['buildingId'])['elevation']=999
        previous,_,_=derive_recessed_entry_site(self.config,cached,self.sources)
        self.assertEqual(site,previous)
        self.assertNotIn('buildingElevation',site)

    def test_prepare_sites_with_fresh_building_records(self):
        from site_data import prepare_sites
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);out=root/'public/data';out.mkdir(parents=True)
            shutil.copytree(ROOT/'data',root/'data')
            for name in ('campus-roads','surfaces','infrastructure','surroundings','sources','vegetation','overview'):
                shutil.copyfile(ROOT/f'public/data/{name}.json',out/f'{name}.json')
            fresh=copy.deepcopy(self.buildings)
            for b in fresh:
                for key in ('elevation','chunk','zone'):b.pop(key,None)
            (out/'buildings.json').write_text(json.dumps(fresh))
            self.assertFalse((out/'sites.json').exists())
            with contextlib.redirect_stdout(io.StringIO()):prepare_sites(root)
            prepared=json.loads((out/'sites.json').read_text())
            site=next(s for s in prepared['sites'] if s['id']==self.config['id'])
            self.assertNotIn('buildingElevation',site)
            self.assertEqual(site['buildingCenter'],next(b['center'] for b in fresh if b['id']==self.config['buildingId']))
            self.assertGreater(Polygon(site['pavingPolygon']).area,1100)
            self.assertEqual(json.loads((out/'buildings.json').read_text()),fresh)


if __name__=='__main__':unittest.main()
