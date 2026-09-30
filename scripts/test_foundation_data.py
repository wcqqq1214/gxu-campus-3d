import json
import tempfile
import unittest
from pathlib import Path
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from foundation_data import prepare_foundations
from foundation_contract import load_foundations


class FoundationPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'public/data').mkdir(parents=True);(self.root/'data').mkdir()
        polygon=lambda x0,y0,x1,y1:[[[[x0,y0],[x1,y0],[x1,y1],[x0,y1],[x0,y0]]]]
        self.buildings=[{'id':'test','center':[2,2],'polygons':polygon(0,0,4,4),'form':{'parts':[
            {'id':'closed','polygons':polygon(0,0,4,4)},
            {'id':'open','polygons':polygon(10,0,12,4),'openBelow':{'floorHeight':1}}]}}]
        values={'buildings':self.buildings,'terrain':{'cols':2,'rows':2,'bounds':[-20,-20,20,20],'heights':[2,2,2,2]},
                'surfaces':[],'infrastructure':{'surfaceOverrides':{},'replaceSurfaceIds':[]},
                'surroundings':{'surfaceOverrides':{},'layers':[]},'campus-roads':{'surfaceOverrides':{},'layers':[]},
                'sites':{'surfaceOverrides':{},'sites':[]},'pavings':{},'shores':{}}
        for key,value in values.items():self.write(key,value)
        self.config={'schemaVersion':1,'foundations':[{'id':'repair','buildingId':'test','coreMargin':.1,'roadTrimMargin':.4,'haloMeters':6,'groundOffset':0}]}
        (self.root/'data/foundation-overrides.json').write_text(json.dumps(self.config))

    def write(self,name,value):
        (self.root/'public/data'/f'{name}.json').write_text(json.dumps(value))

    def test_fresh_preparation_has_no_exporter_fields_and_excludes_open_part(self):
        prepare_foundations(self.root)
        r=load_foundations(self.root)['foundations'][0]
        self.assertEqual(r['datum'],2)
        core=unary_union([Polygon(p[0],p[1:]) for p in r['corePolygons']])
        self.assertTrue(core.contains(Point(2,2)))
        self.assertFalse(core.contains(Point(11,2)))
        self.assertAlmostEqual(r['closedArea'],16)

    def test_exporter_fields_do_not_stale_masks_but_geometry_changes_do(self):
        prepare_foundations(self.root)
        self.buildings[0].update(elevation=2,zone='academic',chunk='chunk-test');self.write('buildings',self.buildings)
        load_foundations(self.root)
        self.buildings[0]['center']=[3,2];self.write('buildings',self.buildings)
        with self.assertRaisesRegex(ValueError,'stale'):load_foundations(self.root)

    def test_protected_site_cannot_be_cut_through_closed_floor(self):
        self.write('sites',{'surfaceOverrides':{},'sites':[{'gradingBounds':[1,1,2,2]}]})
        with self.assertRaisesRegex(ValueError,'protected'):prepare_foundations(self.root)

    def test_config_change_requires_repreparation(self):
        prepare_foundations(self.root)
        self.config['foundations'][0]['haloMeters']=5
        (self.root/'data/foundation-overrides.json').write_text(json.dumps(self.config))
        with self.assertRaisesRegex(ValueError,'stale'):load_foundations(self.root)

    def test_simplification_limits_are_checked_before_preparation(self):
        for value in [{'weldDistance':.001},{'normalTolerance':.001},
                      {'weldDistance':float('nan')},{'normalTolerance':True},
                      {'normalTolerance':0},{'other':.0001},[]]:
            with self.subTest(value=value):
                self.config['foundations'][0]['meshSimplification']=value
                (self.root/'data/foundation-overrides.json').write_text(json.dumps(self.config))
                with self.assertRaisesRegex(ValueError,'simplification'):
                    prepare_foundations(self.root)

    def test_bounded_simplification_survives_freshness_contract(self):
        settings={'normalTolerance':1e-4,'weldDistance':1e-4}
        self.config['foundations'][0]['meshSimplification']=settings
        (self.root/'data/foundation-overrides.json').write_text(json.dumps(self.config))
        prepare_foundations(self.root)
        self.assertEqual(load_foundations(self.root)['foundations'][0]['meshSimplification'],settings)

    def test_road_conform_margin_is_bounded_and_fresh(self):
        self.config['foundations'][0]['roadExportConformMargin']=15
        (self.root/'data/foundation-overrides.json').write_text(json.dumps(self.config))
        prepare_foundations(self.root)
        self.assertEqual(load_foundations(self.root)['foundations'][0]['roadExportConformMargin'],15)
        for value in [0,-1,51,True,float('nan')]:
            self.config['foundations'][0]['roadExportConformMargin']=value
            (self.root/'data/foundation-overrides.json').write_text(json.dumps(self.config))
            with self.assertRaisesRegex(ValueError,'conform margin'):prepare_foundations(self.root)

    def test_unpartitioned_building_can_limit_repair_without_filling_courtyard(self):
        self.buildings[0]['form']['parts']=[]
        self.buildings[0]['polygons'][0].append([[1,1],[1,3],[3,3],[3,1],[1,1]])
        self.write('buildings',self.buildings)
        self.config['foundations'][0]['repairBounds']=[-1,-1,2,5]
        (self.root/'data/foundation-overrides.json').write_text(json.dumps(self.config))
        prepare_foundations(self.root)
        r=load_foundations(self.root)['foundations'][0]
        core=unary_union([Polygon(p[0],p[1:]) for p in r['corePolygons']])
        self.assertTrue(core.contains(Point(.5,2)))
        self.assertFalse(core.contains(Point(1.5,2)))
        self.assertFalse(core.contains(Point(3.5,2)))
        self.assertAlmostEqual(r['closedArea'],6)
        self.assertAlmostEqual(r['buildingClosedArea'],12)

    def test_invalid_or_empty_repair_bounds_rejected(self):
        for bounds in [[0,0,0,1],[0,0,1],[0,0,True,1],[0,0,float('inf'),1],[20,20,21,21]]:
            with self.subTest(bounds=bounds):
                self.config['foundations'][0]['repairBounds']=bounds
                (self.root/'data/foundation-overrides.json').write_text(json.dumps(self.config))
                with self.assertRaisesRegex(ValueError,'repair bounds'):
                    prepare_foundations(self.root)


if __name__=='__main__':unittest.main()
