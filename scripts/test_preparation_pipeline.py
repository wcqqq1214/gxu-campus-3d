"""Full and incremental scene preparation must use the same displayed context."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from shapely.geometry import Polygon, box
from context_data import select_context
from surroundings_data import building_obstacles
from building_overrides import source_catalogue


class PreparationPipelineTests(unittest.TestCase):
    def test_sources_prepare_without_public_outputs_and_reject_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'data').mkdir()
            names=('sources.json','huicui-sources.json',
                   'basketball-sources.json','building-sources.json')
            for i,name in enumerate(names):
                (root/'data'/name).write_text(json.dumps([{'id':f'source-{i}'}]))
            self.assertEqual([s['id'] for s in source_catalogue(root)],
                             [f'source-{i}' for i in range(4)])
            self.assertFalse((root/'public').exists())
            (root/'data/building-sources.json').write_text('[{"id":"source-0"}]')
            with self.assertRaisesRegex(ValueError,'Duplicate source ID'):
                source_catalogue(root)

    def building(self, ident, footprint, inside=False):
        return {'id':ident,'name':ident,'insideCampus':inside,
                'polygons':[[list(footprint.exterior.coords)] +
                            [list(r.coords) for r in footprint.interiors]]}

    def test_omitted_context_does_not_cut_holes_in_perimeter_roads(self):
        campus=box(0,0,100,100)
        near=self.building('adjacent',box(110,40,115,50))
        distant=self.building('omitted',box(150,40,155,50))
        raw=[near,distant];original=copy.deepcopy(raw)
        retained,_=select_context(raw,campus)
        road=box(100,35,180,55)
        full=road.difference(building_obstacles(raw,campus))
        incremental=road.difference(building_obstacles(retained,campus))
        self.assertLess(full.symmetric_difference(incremental).area,1e-9)
        self.assertTrue(full.covers(box(150,40,155,50)))
        self.assertTrue(full.disjoint(box(110,40,115,50).buffer(2.19)))
        self.assertEqual(raw,original)

    def test_boundary_distance_and_courtyard_are_preserved(self):
        campus=box(0,0,100,100)
        on_boundary=self.building('20m',box(120,40,130,50))
        outside=self.building('over20m',box(120.01,60,130,70))
        courtyard=Polygon([(20,20),(80,20),(80,80),(20,80)],
                          [[(30,30),(70,30),(70,70),(30,70)]])
        inside=self.building('courtyard',courtyard,True)
        mask=building_obstacles([on_boundary,outside,inside],campus)
        self.assertTrue(mask.covers(box(120,40,130,50)))
        self.assertTrue(mask.disjoint(box(120.01,60,130,70)))
        self.assertTrue(mask.disjoint(box(40,40,60,60)))


if __name__=='__main__':
    unittest.main()
